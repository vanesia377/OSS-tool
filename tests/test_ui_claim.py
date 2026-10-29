from streamlit.testing.v1 import AppTest

def test_claim_page_has_seven_blocks_and_real_outputs():
    app=AppTest.from_string("import ui.app as dashboard\ndashboard.claim_page('P1')", default_timeout=30).run()
    assert not app.exception
    labels=[s.value for s in app.subheader]
    assert len([s for s in labels if s[:1].isdigit()])==7
    run=next(b for b in app.button if b.label=='Chạy')
    run.click().run(timeout=30)
    assert not app.exception
    assert any('CONFIRMED' in m.value for m in app.markdown)
