# ==============================================================================
# EXPERIMENT B | Streamlit Platform / Network Round Trip Probe
# 목적:
#   Python 내부 실행시간이 아니라
#   브라우저 → Streamlit 서버/플랫폼 → 브라우저 왕복시간을 측정한다.
#
# A와 동일:
#   - GTL 없음
#   - Google Sheets 없음
#   - 외부 API 없음
#   - 대형 DataFrame 없음
#
# B에서 추가:
#   - 브라우저에서 Streamlit health endpoint를 직접 호출
#   - HTTP 왕복시간을 performance.now()로 측정
# ==============================================================================

# ------------------------------------------------------------------------------
# 0.00.00 | Imports
# ------------------------------------------------------------------------------
import json
import os
import time
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components


# ------------------------------------------------------------------------------
# 0.01.00 | Basic Page
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="EMPTY Streamlit Probe B",
    layout="centered",
)

_run_started = time.perf_counter()
_run_wall = datetime.now().astimezone()

_HISTORY_FILE = "/tmp/empty_streamlit_probe_b_history.jsonl"


# ------------------------------------------------------------------------------
# 0.02.00 | Server History
# ------------------------------------------------------------------------------
def _save_probe_b_record(record):
    try:
        with open(_HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                ) + "\n"
            )
    except Exception:
        pass


def _load_probe_b_history(limit=20):
    try:
        if not os.path.exists(_HISTORY_FILE):
            return []

        rows = []

        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f.readlines()[-limit:]:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass

        return rows

    except Exception:
        return []


# ------------------------------------------------------------------------------
# 0.03.00 | Pure Python Sensor
# ------------------------------------------------------------------------------
_sensor_start = time.perf_counter()

_probe_value = 1 + 1

_sensor_ms = (
    time.perf_counter() - _sensor_start
) * 1000


# ------------------------------------------------------------------------------
# 0.04.00 | Server Execution Sensor
# ------------------------------------------------------------------------------
_server_total_ms = (
    time.perf_counter() - _run_started
) * 1000


_save_probe_b_record({
    "timestamp": _run_wall.strftime("%Y-%m-%d %H:%M:%S"),
    "server_total_ms": round(_server_total_ms, 1),
    "python_sensor_ms": round(_sensor_ms, 1),
})


# ------------------------------------------------------------------------------
# 0.05.00 | Minimal UI
# ------------------------------------------------------------------------------
st.title("🧪 EMPTY Streamlit Probe B")

st.metric(
    "Python 서버 실행시간",
    f"{_server_total_ms:.1f} ms",
)

st.metric(
    "Python 센서 구간",
    f"{_sensor_ms:.1f} ms",
)

st.caption(
    "GTL / Google Sheets / 외부 API / 대형 데이터 / 복잡한 UI를 제거하고 "
    "플랫폼 왕복시간을 별도로 측정합니다."
)


# ------------------------------------------------------------------------------
# 0.06.00 | Browser → Streamlit Health Endpoint Round Trip Sensor
# ------------------------------------------------------------------------------
components.html(
    """
    <div id="probe_b"
         style="
            font-family:sans-serif;
            font-size:16px;
            padding:12px 0;
         ">
        🔄 플랫폼 왕복 센서 측정 중...
    </div>

    <script>
    (async () => {
        const target =
            window.location.origin +
            "/_stcore/health?probe=" +
            Date.now();

        const started = performance.now();

        try {
            const response = await fetch(
                target,
                {
                    method: "GET",
                    cache: "no-store",
                    credentials: "same-origin"
                }
            );

            const elapsed =
                performance.now() - started;

            const box =
                document.getElementById("probe_b");

            box.innerText =
                "🌐 브라우저 ↔ Streamlit 왕복: "
                + elapsed.toFixed(1)
                + " ms"
                + " | HTTP "
                + response.status;

            console.log(
                "[EMPTY PROBE B] round trip = "
                + elapsed.toFixed(1)
                + " ms"
                + " | HTTP "
                + response.status
            );

        } catch (error) {

            const elapsed =
                performance.now() - started;

            const box =
                document.getElementById("probe_b");

            box.innerText =
                "❌ 플랫폼 왕복 측정 실패: "
                + elapsed.toFixed(1)
                + " ms";

            console.error(
                "[EMPTY PROBE B] "
                + error
            );
        }
    })();
    </script>
    """,
    height=55,
)


# ------------------------------------------------------------------------------
# 0.07.00 | Accumulated Server History
# ------------------------------------------------------------------------------
st.subheader("🔍 EMPTY B 누적 기록")

history = _load_probe_b_history(limit=20)

if history:

    for idx, item in enumerate(
        reversed(history),
        start=1
    ):
        st.write(
            f"{idx}. {item['timestamp']} | "
            f"SERVER={item['server_total_ms']}ms | "
            f"PYTHON={item['python_sensor_ms']}ms"
        )

else:

    st.caption(
        "아직 서버 측 기록이 없습니다."
    )


# ------------------------------------------------------------------------------
# 0.08.00 | Interpretation
# ------------------------------------------------------------------------------
st.divider()

st.markdown(
    """
### 🧪 실험 B의 목적

이번에는 두 영역을 분리합니다.

**① Python 서버 실행**

`Python 서버 실행시간`

→ Streamlit Python 코드 자체가 실행되는 시간


**② 플랫폼/네트워크 왕복**

`🌐 브라우저 ↔ Streamlit 왕복`

→ 브라우저에서 Streamlit 서버의 health endpoint까지
갔다가 돌아오는 HTTP 왕복시간


### 판정

**A처럼 Python은 0ms인데 B의 왕복시간이 3~4초로 튄다**

→ GTL 내부 계산 문제가 아니라
브라우저 / 네트워크 / Streamlit Cloud / 플랫폼 계층을 강하게 의심.


**Python도 빠르고 왕복도 빠르다**

→ EMPTY 환경 자체는 정상.
→ 다음 단계에서 GTL을 조금씩 복원.


**10분 후 왕복시간만 튄다**

→ 우리가 찾던 "10분 장벽"이
GTL 코드가 아닌 플랫폼/네트워크 계층에서 재현되는지 확인 가능.
"""
)
