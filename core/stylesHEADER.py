import streamlit as st


def apply_stylesHEADER():
    st.markdown(
        """
        <style>
        .avant-header-spacer {
            height: 88px;
        }

        .avant-header-wrap {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 999;
            padding: 10px 18px 8px 18px;
            background: rgba(246, 248, 254, 0.88);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--panel-border);
            box-shadow: var(--shadow-lg);
            animation: avantHeaderFadeIn 0.35s ease-out;
        }

        .avant-header-grid {
            display: grid;
            grid-template-columns: minmax(240px, 1fr) minmax(280px, 560px) minmax(220px, 1fr);
            align-items: center;
            gap: 14px;
            width: 100%;
        }

        .avant-header-left {
            display: flex;
            align-items: center;
            gap: 14px;
            min-width: 0;
        }

        .avant-header-logo {
            height: 46px;
            width: auto;
        }

        .avant-header-brand {
            font-size: clamp(1.05rem, 1.7vw, 1.45rem);
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: var(--accent-strong);
        }

        .avant-header-version {
            font-size: 11px;
            color: var(--text-muted);
        }

        .avant-header-center {
            display: flex;
            justify-content: center;
        }

        .avant-header-subtitle {
            font-size: clamp(0.95rem, 1.4vw, 1.2rem);
            font-weight: 600;
            color: var(--text-primary);
            letter-spacing: 0.03em;
        }

        .avant-header-right {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            flex-wrap: wrap;
        }

        .avant-header-pill {
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 600;
            border: 1px solid var(--panel-border);
            background: var(--panel-bg);
            color: var(--text-secondary);
        }

        @keyframes avantHeaderFadeIn {
            from {
                opacity: 0;
                transform: translateY(-8px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @media (max-width: 1100px) {
            .avant-header-grid {
                grid-template-columns: 1fr;
                text-align: center;
            }

            .avant-header-left,
            .avant-header-center,
            .avant-header-right {
                justify-content: center;
            }

            .avant-header-right {
                gap: 6px;
            }

            .avant-header-spacer {
                height: 136px;
            }
        }

        @media (max-width: 640px) {
            .avant-header-wrap {
                padding: 10px 12px 8px 12px;
            }

            .avant-header-logo {
                height: 38px;
            }

            .avant-header-spacer {
                height: 148px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
