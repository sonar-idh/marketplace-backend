## Test Cases
### Test types:
- Regression tests:
    - BIBFRAME Analysis Test
    - MARC Analysis Test
- Unit tests
    - data quality: rda, ger, full encoding level
    - Comparing MARC and BIBFRAME data


Currently test data:

- schumann_example.xml
- schumann.xml, 
- mvp_data_merged.xml
- mvp_test_quality_fail.xml : 040 is rda/ger but leader/17 is '2': must NOT count in rda_ger_encoding
- mvp_test_quality_pass.xml : 040 is rda/ger and leader/17 is blank: counted in rda_ger_encoding
