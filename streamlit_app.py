import os
import threading
import subprocess
from io import BytesIO
from pathlib import Path
import pandas as pd
import streamlit as st
import analysis_engine as engine

st.set_page_config(page_title='영상 자막·음성 분석', layout='wide')
st.markdown("<style>div[data-testid='stVideo']{max-width:640px;margin:auto}video{max-height:300px;object-fit:contain}</style>", unsafe_allow_html=True)
if 'view' not in st.session_state:
    st.session_state['view'] = 'intro'
if st.session_state['view'] == 'intro':
    _, center, _ = st.columns([1, 4, 1])
    with center:
        st.caption('프로그램 안내')
        st.title('영상 속 자막과 목소리를 시간별 텍스트로 정리하세요.')
        st.write('영상을 업로드하면 CG 자막과 발화 내용을 한 표에 정리합니다. GPT-6 Luna로 화면을 검토하고 카드 상품 언급과 오탈자 후보를 확인한 뒤 엑셀로 저장할 수 있습니다.')
        st.info('영상 업로드 → 음성·화면 분석 → GPT 검토 → 엑셀 저장')
        st.write('처음이라면 다음 화면의 ‘시현 시작 · 15초’로 체험해 보세요.')
        st.caption('분석 결과는 영상과 대조해 확인해 주세요. GPT 검토 시 화면 이미지와 인식 텍스트가 OpenAI로 전송되며 API 사용료가 발생합니다.')
        if st.button('다음 · 프로그램 시작 →', type='primary'):
            st.session_state['view'] = 'app'
            st.rerun()
    st.stop()
if st.button('← 프로그램 소개'):
    st.session_state['view'] = 'intro'
    st.rerun()

DEMO_VIDEO = Path(__file__).resolve().parent / 'assets' / '히트 상품에 숨겨진 비밀! 현대카드 데이터 사이언스의 힘.mp4'
heading, demo_column = st.columns([4, 1])
with heading:
    st.title('영상 자막·음성 분석')
with demo_column:
    demo_clicked = st.button('시현 시작 · 15초', disabled=not DEMO_VIDEO.is_file(), help='포함된 원본 영상의 처음 15초를 실제 분석합니다.')
st.caption('음성 인식 → 화면 분석 → GPT-6 Luna 검토 → 엑셀 다운로드')
st.info('영상은 배포 서버로 업로드됩니다. GPT 검토 시 화면 이미지와 OCR·음성 인식 텍스트가 OpenAI로 전송되며 API 사용료가 발생합니다.')

@st.cache_resource
def analysis_lock():
    return threading.Lock()

def get_key():
    value = os.environ.get('OPENAI_API_KEY', '').strip()
    if value:
        return value
    try:
        return str(st.secrets.get('OPENAI_API_KEY', '')).strip()
    except FileNotFoundError:
        return ''

with st.sidebar:
    st.header('분석 설정')
    interval = st.selectbox('화면 검사 간격 (초)', [0.5, 1, 2, 3, 5], index=1)
    crop = st.slider('화면 위쪽 제외 (%)', 0, 80, 0, 5)
    model = st.selectbox('음성 인식 모델', ['base', 'small', 'medium'])
    cards = st.text_area('카드 상품명 (한 줄에 하나)')
    corrections = st.text_area('오탈자 사전', placeholder='이 상 => 이상')
    follow = st.checkbox('영상 화면을 분석 위치로 이동', value=False)
    st.caption('기본 영상 재생은 수동입니다. 위치 이동을 켜면 분석 시점에 따라 플레이어가 다시 표시됩니다.')

upload = st.file_uploader('영상 파일', type=['mp4', 'mov', 'mkv', 'webm', 'avi'])
preview = st.empty()
if upload:
    preview.video(upload.getvalue())

start_clicked = st.button('분석 시작', type='primary')
if start_clicked or demo_clicked:
    key = get_key()
    if not upload and not demo_clicked:
        st.warning('영상 파일을 선택해 주세요.')
    elif not key:
        st.error('Streamlit Secrets에 OPENAI_API_KEY를 설정해 주세요.')
    elif not analysis_lock().acquire(blocking=False):
        st.warning('다른 영상이 분석 중입니다. 잠시 후 다시 시도해 주세요.')
    else:
        st.session_state.pop('result', None)
        st.session_state.pop('result_name', None)
        source_name = DEMO_VIDEO.stem + '_시현' if demo_clicked else Path(upload.name).stem
        source_bytes = DEMO_VIDEO.read_bytes() if demo_clicked else upload.getvalue()
        preview.video(source_bytes)
        bar = st.progress(0)
        status = st.empty()
        class Progress(dict):
            last_position = None
            def update(self, *args, **kwargs):
                super().update(*args, **kwargs)
                bar.progress(max(0, min(100, int(self.get('progress', 0)))))
                status.info(self.get('message', '분석 준비 중입니다.'))
                position = self.get('position')
                if follow and position is not None and self.get('phase') != 'gpt':
                    point = (self.get('phase'), int(position))
                    if point != self.last_position:
                        preview.video(source_bytes, start_time=int(position))
                        self.last_position = point
        job = Progress()
        try:
            with engine.work_directory() as temp:
                path = temp / 'input.mp4'
                if demo_clicked:
                    import imageio_ffmpeg
                    status.info('포함된 원본 영상에서 시현용 15초를 준비합니다.')
                    proc = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-i', str(DEMO_VIDEO), '-t', '15', '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', str(path)], capture_output=True)
                    if proc.returncode:
                        raise RuntimeError('시현 영상 준비에 실패했습니다.')
                else:
                    path.write_bytes(source_bytes)
                pairs = [tuple(part.strip() for part in line.split('=>', 1)) for line in corrections.splitlines() if '=>' in line]
                result = engine.analyze(path, job, interval, crop, model, [x.strip() for x in cards.splitlines() if x.strip()], pairs, key)
            st.session_state['result'] = pd.DataFrame(result)
            st.session_state['result_name'] = source_name + '_분석_결과.xlsx'
            bar.progress(100)
            if job.get('warning'):
                status.warning(job['warning'])
            else:
                status.success('분석 및 GPT 검토 완료')
        except Exception as exc:
            status.error(f'분석 실패: {type(exc).__name__}: {exc}')
        finally:
            analysis_lock().release()

if 'result' in st.session_state:
    st.subheader('통합 결과 검토')
    st.caption('OCR·음성 인식·GPT 검토 결과에는 오류가 있을 수 있습니다. 영상과 대조해 수정한 뒤 저장하세요.')
    edited = st.data_editor(st.session_state['result'], use_container_width=True, num_rows='dynamic', key='result_editor')
    out = BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        edited.to_excel(writer, sheet_name='분석 결과', index=False)
        sheet = writer.sheets['분석 결과']
        sheet.freeze_panes = 'C2'
        sheet.auto_filter.ref = sheet.dimensions
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
        for cell in sheet[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='3267EA')
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical='top', wrap_text=True)
        for i in range(1, sheet.max_column + 1):
            sheet.column_dimensions[get_column_letter(i)].width = 18 if i <= 2 else 45
    st.download_button('엑셀 다운로드', out.getvalue(), file_name=st.session_state['result_name'], mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
