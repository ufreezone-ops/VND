import json
import os
import time
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

# 0.00.00 | EMPTY Streamlit Probe
# 외부 통신 / GTL 로직 / 대형 데이터 없이 실행환경만 측정한다.

# 0.01.00 | Basic Page
st.set_page_config(page_title="EMPTY Streamlit Probe", layout="centered")

_run_started = time.perf_counter()
_run_wall = datetime.now().astimezone()
_history_file = "/tmp/empty_streamlit_probe_history.jsonl"


# 0.02.00 | History Writer
def _save_probe_record(record):
    try:
        with open(_history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _load_probe_history(limit=20):
    try:
        if not os.path.exists(_history_file):
            return []
        rows = []
        with open(_history_file, "r", encoding="utf-8") as f:
            for line in f.readlines()[-limit:]:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
        return rows
    except Exception:
        return []


# 0.03.00 | Server Sensor
_sensor_start = time.perf_counter()

# 의도적인 작업 없음
_probe_value = 1 + 1

_sensor_ms = (time.perf_counter() - _sensor_start) * 1000


# 0.04.00 | Server Total Sensor
_total_ms = (time.perf_counter() - _run_started) * 1000

_save_probe_record({
    "timestamp": _run_wall.strftime("%Y-%m-%d %H:%M:%S"),
    "total_server_ms": round(_total_ms, 1),
    "sensor_ms": round(_sensor_ms, 1),
})


# 0.05.00 | Minimal UI
st.title("🧪 EMPTY Streamlit Probe")
st.metric("서버 실행시간", f"{_total_ms:.1f} ms")
st.metric("센서 구간", f"{_sensor_ms:.1f} ms")

st.caption(
    "Google Sheets / 외부 API / GTL 계산 / 대형 데이터 / 복잡한 UI를 "
    "모두 제거한 순수 Streamlit 실행 실험입니다."
)


# 0.06.00 | Browser Sensor
# iframe 자체의 실행시간을 참고값으로 표시한다.
# 전체 Streamlit 페이지 렌더링 시간과 동일한 값은 아니다.
components.html(
    """
    <script>
    const started = performance.now();
    window.addEventListener("load", () => {
        const elapsed = performance.now() - started;
        const box = document.createElement("div");
        box.style.fontFamily = "sans-serif";
        box.style.fontSize = "16px";
        box.style.padding = "10px";
        box.innerText =
            "브라우저 센서 iframe 실행: " + elapsed.toFixed(1) + " ms";
        document.body.appendChild(box);
        console.log("[EMPTY PROBE] browser iframe = "
            + elapsed.toFixed(1) + " ms");
    });
    </script>
    """,
    height=50,
)


# 0.07.00 | Accumulated History
st.subheader("🔍 EMPTY 누적 기록")

history = _load_probe_history()

if history:
    for idx, item in enumerate(reversed(history), start=1):
        st.write(
            f"{idx}. {item['timestamp']} | "
            f"TOTAL={item['total_server_ms']}ms | "
            f"SENSOR={item['sensor_ms']}ms"
        )
else:
    st.caption("아직 기록이 없습니다.")


# 0.08.00 | Experiment Guide
st.divider()
st.markdown(
    """
### 🧪 실험 규칙

1. 평상시 새로고침을 2회 정도 측정한다.
2. **10분 동안 아무 조작도 하지 않는다.**
3. 10분 후 새로고침한다.
4. 서버 실행시간과 화면 상단 반응속도를 비교한다.

### 판정

- EMPTY도 10분 후 느려진다
  → GTL 내부 로직과 무관한 실행환경/플랫폼 계층을 의심.

- EMPTY는 정상인데 GTL만 느려진다
  → GTL 내부 또는 GTL이 사용하는 외부 서비스/캐시 계층을 의심.

이 실험에서는 기존 GTL 코드를 수정하지 않는다.
"""
)

# 0.09.00 | End
