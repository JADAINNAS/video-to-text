# Streamlit 배포용 영상 분석 앱

이 폴더만 새 GitHub 저장소에 올려 Streamlit Community Cloud에서 배포하세요. 개인 PC의 `.env`, `.deps`, 모델 파일, 개인 업로드 영상은 포함되어 있지 않습니다. 시현용 원본 영상은 assets 폴더에 포함되어 있습니다.

## 배포

1. 이 폴더의 파일과 `.streamlit/config.toml`을 GitHub 저장소에 업로드합니다. 숨김 파일인 `.gitignore`도 포함하세요.
2. Streamlit Community Cloud에서 해당 저장소를 선택합니다.
3. Main file path를 `streamlit_app.py`로 지정합니다. 상위 저장소 아래 폴더째 업로드했다면 `streamlit_deploy/streamlit_app.py`를 지정합니다.
4. Advanced settings에서 Python 3.12를 선택합니다.
5. Secrets에 아래 형식으로 실제 API 키를 입력합니다. `secrets.example.toml`은 형식 안내용이며 실제 키가 들어 있지 않습니다.

```toml
OPENAI_API_KEY = "실제 API 키"
```

6. Deploy를 누릅니다. 모델은 첫 분석 시 자동 다운로드됩니다.

실제 키를 GitHub에 올리지 마세요. `.env`를 이 폴더로 복사할 필요는 없습니다. 로컬 Streamlit 시험 시에는 `.streamlit/secrets.toml`에 같은 형식을 넣을 수 있습니다.

## 파일 구성

- `streamlit_app.py`: 업로드, 진행 상태, 결과 편집, 엑셀 다운로드
- `analysis_engine.py`: 로컬 음성·OCR 분석 및 GPT-6 Luna 화면 검토
- `requirements.txt`: Python 의존성
- `packages.txt`: Linux 의존성
- `.streamlit/config.toml`: 업로드 한도 200MB와 화면 설정
- `secrets.example.toml`: API 키 설정 형식 예시
- `.gitignore`: 키, 모델, 임시 파일, 영상의 커밋 제외 설정

## 동작 및 한계

음성 분석 → 화면 분석 → GPT 검토 순서입니다. 영상은 배포 서버로 업로드되며, 추출 화면과 OCR·음성 인식 텍스트는 OpenAI에 전송됩니다. API 사용료는 Secrets에 설정한 키의 계정으로 발생합니다.

우측 상단의 시현 시작 · 15초 버튼은 assets에 포함된 원본 영상의 처음 15초를 실제 분석합니다. 전체 영상은 파일 업로드로 분석할 수 있습니다. assets 폴더와 원본 MP4도 GitHub에 함께 올려야 시현 버튼이 활성화됩니다. 결과 다운로드 이름은 업로드 영상 제목을 따릅니다. 결과는 세션 동안 유지되며 영구 저장되지 않습니다.

CPU에서 모델을 실행하므로 Cloud의 메모리·CPU 제한에 따라 느리거나 종료될 수 있습니다. 먼저 짧은 영상과 `base` 모델로 확인하세요. 실제 Cloud 배포 및 전체 영상 분석은 이 패키지에서 검증하지 않았습니다. 모델 정확도와 자막 구간 묶음은 수동 검토가 필요합니다.

API 키를 공유하는 앱이므로 공개 범위는 Streamlit의 배포 및 접근 설정에서 관리하세요. 코드에 별도 로그인 기능은 포함되어 있지 않습니다.

## 로컬 실행

```powershell
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```
