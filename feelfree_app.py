# ==============================================================================
# EXPERIMENT B-3 | Real Streamlit App URL Round Trip Probe
# ==============================================================================
#
# 목적
#   ① Python 서버 코드 실행시간
#   ② 실제 Streamlit 앱 URL의 브라우저 HTTP 왕복시간
#
# 을 분리해서 측정한다.
#
# B-2의 document.referrer 방식은 폐기한다.
# B-3에서는 st.context.url을 사용한다.
#
# Streamlit 공식:
#   st.context.url = 사용자가 브라우저에서 접근하는 실제 앱 URL
#
# 정상 HTTP 200만 유효한 측정값으로 인정한다.
# ==============================================================================

import json
import os
import time
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components


# ------------------------------------------------------------------------------
# 0.00.00 | Page Configuration
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="EMPTY Streamlit Probe B-3",
    layout="centered",
)


# ------------------------------------------------------------------------------
# 0.01.00 | Server Execution Timer
# ------------------------------------------------------------------------------
_server_started_at = time.perf_counter()
_server_started_wall = datetime.now().astimezone()

_HISTORY_FILE = "/tmp/empty_streamlit_probe_b3_history.jsonl"


# ------------------------------------------------------------------------------
# 0.02.00 | History Functions
# ------------------------------------------------------------------------------
def _save_probe_b3_record(record):
    try:
        with open(
            _HISTORY_FILE,
            "a",
            encoding="utf-8"
        ) as f:
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                ) + "\n"
            )
    except Exception:
        pass


def _load_probe_b3_history(limit=20):
    try:
        if not os.path.exists(_HISTORY_FILE):
            return []

        rows = []

        with open(
            _HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            for line in f.readlines()[-limit:]:

                try:
                    rows.append(
                        json.loads(line)
                    )
                except Exception:
                    pass

        return rows

    except Exception:
        return []


# ------------------------------------------------------------------------------
# 0.03.00 | Pure Python Sensor
# ------------------------------------------------------------------------------
_sensor_started_at = time.perf_counter()

_probe_value = 1 + 1

_sensor_elapsed_ms = (
    time.perf_counter()
    - _sensor_started_at
) * 1000


# ------------------------------------------------------------------------------
# 0.04.00 | Python Server Execution Measurement
# ------------------------------------------------------------------------------
_server_elapsed_ms = (
    time.perf_counter()
    - _server_started_at
) * 1000


_save_probe_b3_record({
    "timestamp": _server_started_wall.strftime(
        "%Y-%m-%d %H:%M:%S"
    ),
    "server_total_ms": round(
        _server_elapsed_ms,
        1
    ),
    "python_sensor_ms": round(
        _sensor_elapsed_ms,
        1
    ),
})


# ------------------------------------------------------------------------------
# 0.05.00 | Obtain Real Streamlit App URL
# ------------------------------------------------------------------------------
try:
    _app_url = str(
        st.context.url
    ).strip()

except Exception:
    _app_url = ""


# ------------------------------------------------------------------------------
# 0.06.00 | Main UI
# ------------------------------------------------------------------------------
st.title("🧪 EMPTY Streamlit Probe B-3")

st.metric(
    "Python 서버 실행시간",
    f"{_server_elapsed_ms:.1f} ms",
)

st.metric(
    "Python 센서 구간",
    f"{_sensor_elapsed_ms:.1f} ms",
)

st.caption(
    "GTL / Google Sheets / 외부 API / 대형 데이터 / 복잡한 UI를 제거하고 "
    "실제 Streamlit 앱 URL의 HTTP 왕복시간을 측정합니다."
)


# ------------------------------------------------------------------------------
# 0.07.00 | Browser HTTP Round Trip Sensor
# ------------------------------------------------------------------------------
if _app_url:

    # JavaScript 문자열에서 안전하게 사용할 수 있도록 JSON encoding
    _app_url_js = json.dumps(
        _app_url,
        ensure_ascii=False
    )

    components.html(
        f"""
        <div id="probe_b3"
             style="
                 font-family:sans-serif;
                 font-size:16px;
                 padding:12px 0;
                 color:#888;
             ">
            🌐 실제 Streamlit 앱 HTTP 왕복 측정 중...
        </div>

        <script>

        (async () => {{

            const box =
                document.getElementById("probe_b3");

            /*
             * Python의 st.context.url로부터
             * 실제 사용자가 접근 중인 Streamlit 앱 URL을 받는다.
             */
            const target =
                {_app_url_js};

            const started =
                performance.now();

            try {{

                const response =
                    await fetch(
                        target
                        + "?_probe_b3="
                        + Date.now(),
                        {{
                            method: "GET",
                            cache: "no-store",
                            credentials: "include"
                        }}
                    );

                const elapsed =
                    performance.now()
                    - started;

                /*
                 * HTTP 200만 유효한 센서값으로 인정한다.
                 */
                if (response.status === 200) {{

                    box.style.color =
                        "#00c878";

                    box.innerText =
                        "🌐 Streamlit HTTP 왕복: "
                        + elapsed.toFixed(1)
                        + " ms"
                        + " | HTTP 200";

                    console.log(
                        "[EMPTY PROBE B-3] "
                        + "VALID RTT = "
                        + elapsed.toFixed(1)
                        + " ms"
                    );

                }} else {{

                    box.style.color =
                        "#ff6b6b";

                    box.innerText =
                        "❌ 측정 무효: HTTP "
                        + response.status
                        + " | "
                        + elapsed.toFixed(1)
                        + " ms";

                    console.warn(
                        "[EMPTY PROBE B-3] "
                        + "INVALID HTTP = "
                        + response.status
                        + " | "
                        + elapsed.toFixed(1)
                        + " ms"
                    );
                }}

            }} catch (error) {{

                const elapsed =
                    performance.now()
                    - started;

                box.style.color =
                    "#ff6b6b";

                box.innerText =
                    "❌ HTTP 왕복 측정 실패 | "
                    + elapsed.toFixed(1)
                    + " ms";

                console.error(
                    "[EMPTY PROBE B-3] ERROR",
                    error
                );
            }}

        }})();
        </script>
        """,
        height=55,
    )

else:

    st.error(
        "❌ st.context.url을 확인할 수 없습니다."
    )


# ------------------------------------------------------------------------------
# 0.08.00 | Accumulated Server History
# ------------------------------------------------------------------------------
st.subheader("🔍 EMPTY B-3 누적 기록")

_history = _load_probe_b3_history(
    limit=20
)

if _history:

    for idx, item in enumerate(
        reversed(_history),
        start=1
    ):

        st.write(
            f"{idx}. "
            f"{item['timestamp']} | "
            f"SERVER={item['server_total_ms']}ms | "
            f"PYTHON={item['python_sensor_ms']}ms"
        )

else:

    st.caption(
        "아직 서버 측 기록이 없습니다."
    )


# ------------------------------------------------------------------------------
# 0.09.00 | Experiment Guide
# ------------------------------------------------------------------------------
st.divider()

st.markdown(
    """
### 🧪 B-3 실험

이번 실험은 두 시간을 분리합니다.

**① Python 서버 실행시간**

→ Streamlit Python 코드 자체가 실행되는 시간


**② Streamlit HTTP 왕복**

→ 현재 실제 Streamlit 앱 URL에 브라우저가 GET 요청을 보내고
HTTP 200 응답을 받을 때까지의 시간


### ⚠️ 유효성

`HTTP 200`만 정상 측정값입니다.

`404`, `500`, 기타 오류는 측정값으로 인정하지 않습니다.


### 판정

**Python은 매우 빠른데 HTTP 왕복만 수초**

→ Python 코드보다
Streamlit Cloud / 플랫폼 / 네트워크 계층을 우선 의심


**Python과 HTTP 왕복 모두 빠름**

→ EMPTY 환경은 정상


**10분 후 HTTP 왕복만 증가**

→ 기존 GTL에서 발견했던 "10분 장벽"이
EMPTY 환경에서도 재현되는지 확인


**10분 후에도 둘 다 빠름**

→ 플랫폼의 일반적인 10분 지연 가능성이 낮아짐.
→ 그 다음 GTL을 단계적으로 복원해서 범인을 찾는다.
"""
)
