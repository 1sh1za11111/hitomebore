import streamlit as st
import pandas as pd
import re

# ページ設定
st.set_page_config(page_title="詳細分析版・投票集計システム", layout="wide")

st.title("🏆 詳細ランキング集計ツール（全部門統合版）")
st.write("個人別の「ひとめpt」「ぼれpt」の内訳と、それぞれの詳細な感想を1つのリストにまとめます。")

# 1. ファイルアップローダー
vote_file = st.file_uploader("1. 投票結果CSV（Googleフォーム）", type="csv")
mapping_file = st.file_uploader("2. 【任意】ID対応表CSV", type="csv")

def normalize_id(val):
    if pd.isna(val): return None
    return str(val).strip().lstrip('0')

def decorate_rank(rank):
    if rank == 1: return "🥇 1位"
    if rank == 2: return "🥈 2位"
    if rank == 3: return "🥉 3位"
    return f"{rank}位"

if vote_file is not None:
    vote_df = pd.read_csv(vote_file)
    
    # 2. ID対応表の処理
    mapping_dict = {}
    id_to_type = {}
    name_to_ids = {}
    use_mapping = False

    if mapping_file is not None:
        mapping_df = pd.read_csv(mapping_file)
        for _, row in mapping_df.iterrows():
            name = str(row['名前']).strip()
            id1 = normalize_id(row['ID1'])
            id2 = normalize_id(row['ID2'])
            if id1:
                mapping_dict[id1], id_to_type[id1] = name, "A"
            if id2:
                mapping_dict[id2], id_to_type[id2] = name, "B"
            name_to_ids[name] = {"A": id1, "B": id2}
        use_mapping = True
    else:
        st.warning("⚠️ ID対応表がありません。")
        ans = st.radio("このままIDのみで集計しますか？", ("選択してください", "はい", "いいえ"))
        if ans != "はい": st.stop()
        use_mapping = False

    # 3. 集計ロジック
    rank_cols = [c for c in vote_df.columns if "位" in c]
    personal_stats = {}

    for _, row in vote_df.iterrows():
        for col in rank_cols:
            raw_id = normalize_id(row[col])
            if not raw_id: continue

            # カテゴリー（ひとめ/ぼれ）と順位（1/2/3位）
            cat = "ひとめ" if "ひとめ" in col else ("ぼれ" if "ぼれ" in col else "その他")
            rank_num = 1 if '1' in col or '１' in col else (2 if '2' in col or '２' in col else 3)
            points = 4 - rank_num 

            # 感想取得
            col_idx = vote_df.columns.get_loc(col)
            reason = str(row.iloc[col_idx + 1]).strip() if col_idx + 1 < len(vote_df.columns) else ""
            if reason == "nan" or not reason: reason = ""

            p_key = mapping_dict.get(raw_id, raw_id) if use_mapping else raw_id
            
            if p_key not in personal_stats:
                personal_stats[p_key] = {
                    "合計": 0,
                    "ひとめ得点": 0, "ぼれ得点": 0,
                    "ひとめ1位":0, "ひとめ2位":0, "ひとめ3位":0,
                    "ぼれ1位":0, "ぼれ2位":0, "ぼれ3位":0,
                    "A_ひとめ感想": [], "B_ひとめ感想": [], "A_ぼれ感想": [], "B_ぼれ感想": [],
                    "IDのみ感想": []
                }
            
            # 得点と内訳の加算
            personal_stats[p_key]["合計"] += points
            personal_stats[p_key][f"{cat}得点"] += points
            personal_stats[p_key][f"{cat}{rank_num}位"] += 1
            
            # 感想の振り分け
            if use_mapping:
                w_type = id_to_type.get(raw_id, "不明")
                if reason:
                    personal_stats[p_key][f"{w_type}_{cat}感想"].append(reason)
            else:
                if reason:
                    personal_stats[p_key]["IDのみ感想"].append(f"({cat}){reason}")

    # 4. CSV用データの整形（順位順）
    p_rows = []
    for name, s in personal_stats.items():
        ids = name_to_ids.get(name, {"A": "なし", "B": "なし"})
        row = {
            "制作者名": name,
            "総合得点": s["合計"],
            "【ひとめ】合計点": s["ひとめ得点"],
            "【ひとめ】1位票数": s["ひとめ1位"],
            "【ひとめ】2位票数": s["ひとめ2位"],
            "【ひとめ】3位票数": s["ひとめ3位"],
            "【ぼれ】合計点": s["ぼれ得点"],
            "【ぼれ】1位票数": s["ぼれ1位"],
            "【ぼれ】2位票数": s["ぼれ2位"],
            "【ぼれ】3位票数": s["ぼれ3位"],
        }
        if use_mapping:
            row[f"作品A({ids['A']})ひとめ感想"] = " / ".join(s["A_ひとめ感想"])
            row[f"作品A({ids['A']})ぼれ感想"] = " / ".join(s["A_ぼれ感想"])
            row[f"作品B({ids['B']})ひとめ感想"] = " / ".join(s["B_ひとめ感想"])
            row[f"作品B({ids['B']})ぼれ感想"] = " / ".join(s["B_ぼれ感想"])
        else:
            row["感想まとめ"] = " / ".join(s["IDのみ感想"])
            
        p_rows.append(row)

    p_df = pd.DataFrame(p_rows)
    p_df["順位"] = p_df["総合得点"].rank(method="min", ascending=False).astype(int)
    
    # 順位でソートしてから、順位列を一番左に持ってくる
    p_df = p_df.sort_values("順位").reset_index(drop=True)
    cols = ["順位"] + [c for c in p_df.columns if c != "順位"]
    p_df = p_df[cols]

    # 5. 画面表示（TOP 5）
    st.subheader("🥇 個人総合ランキング (TOP 5)")
    display_cols = ["順位", "制制作名", "総合得点", "【ひとめ】合計点", "【ぼれ】合計点"] if "制作者名" in p_df.columns else ["順位", "総合得点"]
    # 実際に存在する列のみ表示
    actual_display_cols = [c for c in ["順位", "制作者名", "総合得点", "【ひとめ】合計点", "【ぼれ】合計点"] if c in p_df.columns]
    
    # メダル装飾版のテーブル
    web_display_df = p_df[p_df["順位"] <= 5].copy()
    web_display_df["順位"] = web_display_df["順位"].apply(decorate_rank)
    st.table(web_display_df[actual_display_cols])

    # 6. ダウンロード
    st.divider()
    st.subheader("📥 全結果のダウンロード")
    csv_data = p_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="全ての順位・得点内訳・感想を含むCSVを保存",
        data=csv_data,
        file_name='full_ranking_report.csv',
        mime='text/csv'
    )