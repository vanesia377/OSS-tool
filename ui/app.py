import sys, time, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st
from core.registry import CLAIMS, PAGES
from core.storage import ROOT, ARTIFACTS, load, verdict
from core.dashboard import start, results, health
from core.models import STATUSES

st.set_page_config(page_title='Playground kiểm chứng OSS', layout='wide')
st.caption('Pha 1 • Ngày tham chiếu 2026-10-29 • Không có kết quả công cụ giả lập')

@st.cache_data(ttl=10)
def infrastructure(): return health()

def overview():
    st.title('Ma trận kiểm chứng')
    st.info('Chỉ P1 kiểm dữ liệu nền. A1–A11 và B1–B14 chưa kiểm chứng; các trang công cụ là khung cho pha sau.')
    rs=results(); vs=load(ARTIFACTS/'verdicts.json',{})
    filters=st.multiselect('Lọc trạng thái',STATUSES,default=list(STATUSES))
    rows=[]
    for k,c in CLAIMS.items():
        r=rs[k]; v=vs.get(k,{})
        if r['status'] in filters:
            rows.append({'ID':k,'Claim':c['title'],'Pha':c['phase'],'Tự động':r['status'],'Thực thi':r['execution'],
                         'Người dùng':v.get('status','Chưa chốt'),'Lệch?':bool(v and v['status']!=r['status'])})
    st.dataframe(rows,use_container_width=True,hide_index=True)
    st.caption('Xuất báo cáo từ bằng chứng và phân tích “Bảng chốt nói quá/thiếu” được triển khai ở Pha 4.')
    st.subheader('Nguồn dữ liệu')
    st.json(load(ROOT/'data/generated/nhtsa_source.json',{'status':'UNVERIFIED','note':'Chưa tải NHTSA'}))

def claim_page(k, page=None):
    c=CLAIMS[k]; st.title(f'{page or k} · {c["title"]}')
    st.subheader('1. Claim gốc & hạ tầng')
    st.text(c['original'])
    h=infrastructure()
    st.write('ClickHouse: '+('UP' if h['up'] else 'DOWN'))
    with st.expander('Bằng chứng trạng thái service'): st.code(h['output'])
    st.caption('ClickHouse: giới hạn cấu hình 4 GiB. RAM các tool khác chưa đo; chưa coi là đủ tài nguyên.')
    if c['phase']>1: st.warning(f'Khung Pha {c["phase"]}: nút Chạy trả UNVERIFIED / NOT_RUN, không chạy tool giả.')
    st.subheader('2. Input chỉnh được')
    question=st.text_area('Câu hỏi tiếng Việt','Tỉ lệ bảo hành giảm chấn sau theo dòng xe quý này so với quý trước?',key=k+'q')
    mode=st.selectbox('Phương án',['Chính','Dự phòng','So sánh'],key=k+'mode')
    left,right=st.columns(2)
    with left:
        abs_tol=st.number_input('abs_tol',min_value=0.0,value=0.01,key=k+'abs')
        horizon=st.number_input('Horizon (tháng)',min_value=1,max_value=24,value=3,key=k+'horizon')
    with right:
        rel_tol=st.number_input('rel_tol',min_value=0.0,value=0.001,key=k+'rel')
        model=st.text_input('Model (không nhập API key)',key=k+'model')
    few=st.checkbox('Few-shot ClickHouse',value=True,key=k+'few')
    heavy=st.checkbox('Bật dịch vụ nặng — chưa đo RAM; không tự khởi động trong Pha 1',key=k+'heavy')
    timeout=st.number_input('Timeout (giây)',min_value=1,max_value=3600,value=60,key=k+'timeout')
    force=st.checkbox('Chạy lại bỏ cache',key=k+'force')
    st.subheader('3. Chạy & log')
    if st.button('Chạy',disabled=c['heavy'] and not heavy,key=k+'run'):
        params=dict(question=question,mode=mode,abs_tol=abs_tol,rel_tol=rel_tol,horizon=horizon,model=model,few_shot=few,heavy=heavy)
        proc,path=start(k,params,int(timeout),force)
        display=st.empty()
        # Live worker output; lifecycle/timeout are owned by core.run.
        while proc.poll() is None:
            display.code(path.read_text()[-12000:]); time.sleep(0.25)
        display.code(path.read_text()[-16000:])
        st.caption(f'CLI exit status: {proc.returncode}')
    r=results()[k]
    st.write(f'Tự động: **{r["status"]}** — {r["summary"]}')
    st.json({x:r.get(x) for x in ('execution','duration','versions','run_id','cache_key')})
    st.subheader('4. So sánh các phương án')
    if not r.get('alternatives'): st.info('Chưa có phép chạy so sánh. Không suy ra ưu/nhược điểm khi chưa đo.')
    else:
        for col,(name,result) in zip(st.columns(len(r['alternatives'])),r['alternatives'].items()):
            with col: st.write(name); st.json(result)
    st.subheader('5. Đối chiếu ground truth')
    if r.get('comparisons'):
        for item in r['comparisons']:
            with st.expander(('✅ ' if item['correct'] else '❌ ')+item['id']):
                st.code(item['sql'],language='sql')
                l,rr=st.columns(2)
                with l: st.write('Chuẩn'); st.json(item['expected'])
                with rr: st.write('Thực tế'); st.json(item['actual'])
    else: st.info('Chưa có output thực để đối chiếu.')
    st.subheader('6. Panel bằng chứng')
    st.json(r.get('evidence',[]))
    st.caption('License, release mới nhất, archived flag: UNVERIFIED cho đến khi tra nguồn ở Pha 2. Version đã cài không phải version mới nhất.')
    st.subheader('7. Phán quyết của người dùng')
    v=load(ARTIFACTS/'verdicts.json',{}).get(k,{})
    choices=['UNVERIFIED','CONFIRMED','PARTIAL','REFUTED']
    status=st.selectbox('Phán quyết',choices,index=choices.index(v.get('status','UNVERIFIED')),key=k+'verdict')
    note=st.text_area('Ghi chú',v.get('note',''),key=k+'note')
    if st.button('Lưu phán quyết',key=k+'save'):
        verdict(k,status,note); v=dict(status=status,note=note); st.success('Đã lưu artifacts/verdicts.json')
    if v and v['status']!=r['status']: st.warning('Phán quyết người dùng lệch với kết quả tự động.')

def group_a():
    st.title('Nhóm A · hồ sơ bằng chứng')
    st.warning('Pha 1: chưa truy vấn GitHub/PyPI/LICENSE. Tất cả claim nhóm A là UNVERIFIED.')
    k=st.selectbox('Chọn claim',[f'A{i}' for i in range(1,12)])
    claim_page(k)
    with st.expander('Danh mục tool, kể cả dự phòng/đã loại'):
        st.dataframe(load(ROOT/'data/tool_inventory.json'),use_container_width=True)

def risks():
    st.title('Rủi ro thực tế')
    st.write('API/model chưa chạy: token và chi phí = chưa đo, không phải 0.')
    st.write('ClickHouse giới hạn 4 GiB, 2 CPU trong Compose. Không suy ra RAM của OpenMetadata/Langfuse.')
    st.json(load(ARTIFACTS/'phase1_environment.json',{'status':'UNVERIFIED'}))
    st.write('Số package khóa:',(ROOT/'uv.lock').read_text().count('[[package]]'))
    st.dataframe([dict(claim=k,duration_seconds=v.get('duration'),execution=v['execution']) for k,v in results().items()])

pages=[st.Page(overview,title='Tổng hợp',default=True),st.Page(lambda:claim_page('P1'),title='Dữ liệu Pha 1'),st.Page(group_a,title='Nhóm A'),st.Page(risks,title='Rủi ro thực tế')]
steps=[]
for page,ids in PAGES.items():
    def render(k=ids[0], name=page): claim_page(k,name)
    steps.append(st.Page(render,title=page,url_path='step_'+page.replace('+','_')))
st.navigation({'Tổng quan':pages,'Bảng chốt':steps}).run()
