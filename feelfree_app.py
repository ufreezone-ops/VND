# ==============================================================================
# EXPERIMENT B-2 | Real Streamlit Document Round Trip Probe
# 목적:
#   GTL / Google Sheets / 외부 API / 대형 데이터 없이
#   현재 실제 Streamlit 앱 URL에 HTTP 요청을 보내
#   브라우저 ↔ Streamlit 플랫폼의 왕복시간을 측정한다.
#
# B-1의 /_stcore/health 는 HTTP 404였으므로 폐기한다.
#
# 핵심:
#   - 404 / 500 등 비정상 응답은 유효 측정값으로 인정하지 않는다.
#   - HTTP 200인 경우에만 RTT를 기록한다.
#   - Python 실행시간도 동시에 측정한다.
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
    page_title="EMPTY Streamlit Probe B-2",
    layout="centered",
)

_run_started = time.perf_counter()
_run_wall = datetime.now().astimezone()

_HISTORY_FILE = "/tmp/empty_streamlit_probe_b2_history.jsonl"


# ------------------------------------------------------------------------------
# 0.02.00 | History Writer
# ------------------------------------------------------------------------------
def _save_probe_b2_record(record):
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


def _load_probe_b2_history(limit=20):
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
_sensor_started = time.perf_counter()

_probe_value = 1 + 1

_sensor_ms = (
    time.perf_counter() - _sensor_started
) * 1000


# ------------------------------------------------------------------------------
# 0.04.00 | Python Total Sensor
# ------------------------------------------------------------------------------
_server_total_ms = (
    time.perf_counter() - _run_started
) * 1000


_save_probe_b2_record({
    "timestamp": _run_wall.strftime("%Y-%m-%d %H:%M:%S"),
    "server_total_ms": round(_server_total_ms, 1),
    "python_sensor_ms": round(_sensor_ms, 1),
})


# ------------------------------------------------------------------------------
# 0.05.00 | Minimal UI
# ------------------------------------------------------------------------------
st.title("🧪 EMPTY Streamlit Probe B-2")

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
    "실제 Streamlit 앱 URL의 HTTP 왕복시간을 측정합니다."
)


# ------------------------------------------------------------------------------
# 0.06.00 | Real App URL HTTP Round Trip Sensor
# ------------------------------------------------------------------------------
components.html(
    """
    <div id="probe_b2"
         style="
            font-family:sans-serif;
            font-size:16px;
            padding:12px 0;
            color:#888;
         ">
        🌐 실제 Streamlit 앱 왕복 측정 중...
    </div>

    <script>
    (async () => {

        const box =
            document.getElementById("probe_b2");

        /*
         * components.html()은 iframe이므로
         * 현재 iframe URL이 아니라 부모 Streamlit 앱 URL을 사용한다.
         *
         * document.referrer가 부모 앱 URL을 제공한다.
         */
        let target =
            document.referrer;

        if (!target) {
            box.innerText =
                "❌ 부모 Streamlit URL을 확인할 수 없습니다.";
            return;
        }

        /*
         * 캐시를 피하기 위해 timestamp query parameter 추가.
         */
        const separator =
            target.includes("?")
                ? "&"
                : "?";

        target =
            target
            + separator
            + "_probe_b2="
            + Date.now();

        const started =
            performance.now();

        try {

            const response =
                await fetch(
                    target,
                    {
                        method: "GET",
                        cache: "no-store",
                        credentials: "include"
                    }
                );

            const elapsed =
                performance.now()
                - started;

            /*
             * HTTP 200만 정상 측정으로 인정.
             */
            if (response.status === 200) {

                box.style.color = "#00c878";

                box.innerText =
                    "🌐 Streamlit HTTP 왕복: "
                    + elapsed.toFixed(1)
                    + " ms"
                    + " | HTTP 200";

                console.log(
                    "[EMPTY PROBE B-2] "
                    + "VALID RTT = "
                    + elapsed.toFixed(1)
                    + " ms"
                );

            } else {

                box.style.color = "#ff6b6b";

                box.innerText =
                    "❌ 측정 무효: HTTP "
                    + response.status
                    + " | "
                    + elapsed.toFixed(1)
                    + " ms";

                console.warn(
                    "[EMPTY PROBE B-2] "
                    + "INVALID HTTP = "
                    + response.status
                    + " | "
                    + elapsed.toFixed(1)
                    + " ms"
                );
            }

        } catch (error) {

            const elapsed =
                performance.now()
                - started;

            box.style.color = "#ff6b6b";

            box.innerText =
                "❌ HTTP 왕복 측정 실패 | "
                + elapsed.toFixed(1)
                + " ms";

            console.error(
                "[EMPTY PROBE B-2] ERROR",
                error
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
st.subheader("🔍 EMPTY B-2 누적 기록")

history = _load_probe_b2_history(limit=20)

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
# 0.08.00 | Experiment Guide
# ------------------------------------------------------------------------------
st.divider()

st.markdown(
    """
### 🧪 B-2 실험

이번 실험에서는 두 시간을 분리해서 봅니다.

**① Python 서버 실행시간**

→ Streamlit Python 코드 자체가 실행되는 시간


**② Streamlit HTTP 왕복**

→ 현재 실제로 열려 있는 Streamlit 앱 URL에
브라우저가 HTTP GET을 보내고 HTTP 200 응답을 받을 때까지의 시간


### ⚠️ 유효성

`HTTP 200`만 정상 측정값입니다.

`404`, `500`, 기타 오류는 **측정값으로 인정하지 않습니다.**


### 판정

**Python은 0ms인데 HTTP 왕복이 3~4초로 증가**

→ GTL Python 계산보다는
플랫폼 / 네트워크 / Streamlit Cloud 계층을 의심.


**Python과 HTTP 왕복 모두 빠름**

→ EMPTY 환경 자체는 정상.
→ 다음 단계에서 GTL을 단계적으로 복원.


**10분 후 HTTP 왕복만 증가**

→ 우리가 찾고 있던 "10분 장벽"이
플랫폼 계층에서 재현되는지 확인할 수 있음.
"""
)
