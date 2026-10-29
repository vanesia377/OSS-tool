from streamlit.testing.v1 import AppTest

def test_summary_shows_unverified_claims():
    app=AppTest.from_file('ui/app.py',default_timeout=20).run()
    assert not app.exception
    assert app.title[0].value=='Ma trận kiểm chứng'
    matrix=app.dataframe[0].value
    assert len(matrix)==26
    assert matrix.loc[matrix['ID']=='B5','Tự động'].iloc[0]=='UNVERIFIED'
