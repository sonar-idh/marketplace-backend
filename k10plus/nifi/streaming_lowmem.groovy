import javax.xml.stream.*
import javax.xml.stream.events.XMLEvent
import org.apache.nifi.processor.io.*
import java.util.zip.GZIPInputStream

//  Each record is written to the chunk while it is read, so memory stays constant
final String NS = 'http://www.loc.gov/MARC21/slim'
final int CHUNK = 8000

def flowFile = session.get()
if (!flowFile) return

def ef  = XMLEventFactory.newInstance()
def xof = XMLOutputFactory.newInstance()
def xif = XMLInputFactory.newInstance()
xif.setProperty(XMLInputFactory.SUPPORT_DTD, false)
xif.setProperty(XMLInputFactory.IS_SUPPORTING_EXTERNAL_ENTITIES, false)

def outs = []
int idx = 0

session.read(flowFile, { InputStream raw ->
    def ins = new GZIPInputStream(new BufferedInputStream(raw, 1 << 16))
    def xr = xif.createXMLEventReader(ins)
    int depth = 0
    boolean more = true
    while (more) {
        int n = 0
        def child = session.create(flowFile)
        child = session.write(child, { OutputStream out ->
            def w = xof.createXMLEventWriter(out, 'UTF-8')
            w.add(ef.createStartDocument('UTF-8', '1.0'))
            w.add(ef.createStartElement('marc', NS, 'collection', null,
                    [ef.createNamespace('marc', NS)].iterator()))
            while (n < CHUNK && xr.hasNext()) {
                XMLEvent ev = xr.nextEvent()
                if (ev.isStartElement()) {
                    depth++
                    if (depth >= 2) w.add(ev)
                } else if (ev.isEndElement()) {
                    if (depth >= 2) w.add(ev)
                    if (depth == 2) n++
                    depth--
                } else if (depth >= 2 && (ev.isCharacters() || ev.getEventType() == XMLStreamConstants.COMMENT)) {
                    w.add(ev)
                }
            }
            w.add(ef.createEndElement('marc', NS, 'collection', null))
            w.add(ef.createEndDocument())
            w.close()
        } as OutputStreamCallback)
        if (n == 0) {
            session.remove(child)       // input ended exactly at a chunk boundary
            more = false
        } else {
            child = session.putAttribute(child, 'chunk.index', String.valueOf(idx++))
            child = session.putAttribute(child, 'chunk.records', String.valueOf(n))
            outs << child
            more = xr.hasNext()
        }
    }
} as InputStreamCallback)

session.transfer(outs, REL_SUCCESS)
session.remove(flowFile)
