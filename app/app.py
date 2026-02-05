import streamlit as st
import pandas as pd
import re

# ページ設定
st.set_page_config(page_title="詳細版・投票集計システム", layout="wide")

st.title("🏆 詳細ランキング集計ツール")
st.write("「ひとめpt」「ぼれpt」の個別集計と、1位〜3位の得票内訳を表示します。")

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
    # カテゴリー（ひとめ/ぼれ）を特定
    categories = {"ひとめ": "ひとめ", "ぼれ": "ぼれ"}
    
    # 個人集計用
    personal_stats = {}
    # 作品単体集計用
    creative_stats = {}

    # 列をループして、どのカテゴリーの何位か特定
    rank_cols = [c for c in vote_df.columns if "位" in c]

    for _, row in vote_df.iterrows():
        for col in rank_cols:
            raw_id = normalize_id(row[col])
            if not raw_id: continue

            # カテゴリー判定
            cat = "ひとめ" if "ひとめ" in col else ("ぼれ" if "ぼれ" in col else "その他")
            # 順位と得点判定
            rank_num = 1 if '1' in col or '１' in col else (2 if '2' in col or '２' in col else 3)
            points = 4 - rank_num # 1位=3pt, 2位=2pt, 3位=1pt

            # 感想の取得
            col_idx = vote_df.columns.get_loc(col)
            reason = str(row.iloc[col_idx + 1]).strip() if col_idx + 1 < len(vote_df.columns) else ""
            if reason == "nan" or not reason: reason = ""

            # --- クリエイティブ（ID）別の集計 ---
            cid_key = (raw_id, cat)
            if cid_key not in creative_stats:
                creative_stats[cid_key] = {"得点": 0, "1位": 0, "2位": 0, "3位": 0, "感想": []}
            creative_stats[cid_key]["得点"] += points
            creative_stats[cid_key][f"{rank_num}位"] += 1
            if reason: creative_stats[cid_key]["感想"].append(reason)

            # --- 個人（名前）別の集計 ---
            p_key = mapping_dict.get(raw_id, raw_id) if use_mapping else raw_id
            if p_key not in personal_stats:
                personal_stats[p_key] = {
                    "合計": 0,
                    "ひとめ得点": 0, "ぼれ得点": 0,
                    "ひとめ内訳": {1:0, 2:0, 3:0}, "ぼれ内訳": {1:0, 2:0, 3:0},
                    "A_reasons": [], "B_reasons": []
                }
            personal_stats[p_key]["合計"] += points
            personal_stats[p_key][f"{cat}得点"] += points
            personal_stats[p_key][f"{cat}内訳"][rank_num] += 1
            
            if use_mapping:
                w_type = id_to_type.get(raw_id, "")
                if reason: personal_stats[p_key][f"{w_type}_reasons"].append(reason)

    # 4. データフレーム変換
    # 4a. 個人総合
    p_rows = []
    for name, s in personal_stats.items():
        p_rows.append({
            "制作者名": name,
            "総合得点": s["合計"],
            "ひとめ得点": s["ひとめ得点"],
            "ぼれ得点": s["ぼれ得点"],
            "ひとめ(1位/2位/3位)": f"{s['ひとめ内訳'][1]} / {s['ひとめ内訳'][2]} / {s['ひとめ内訳'][3]}",
            "ぼれ(1位/2位/3位)": f"{s['ぼれ内訳'][1]} / {s['ぼれ内訳'][2]} / {s['ぼれ内訳'][3]}",
            "作品A感想": " / ".join(s["A_reasons"]) if use_mapping else "",
            "作品B感想": " / ".join(s["B_reasons"]) if use_mapping else ""
        })
    p_df = pd.DataFrame(p_rows)
    p_df["順位"] = p_df["総合得点"].rank(method="min", ascending=False).astype(int)
    p_df = p_df.sort_values("順位").reset_index(drop=True)

    # 4b. クリエイティブ別
    c_rows = []
    for (rid, cat), s in creative_stats.items():
        c_rows.append({
            "ID": rid,
            "制作者": mapping_dict.get(rid, "不明"),
            "区分": cat,
            "得点": s["得点"],
            "1位票": s["1位"], "2位票": s["2位"], "3位票": s["3位"],
            "詳細感想": " / ".join(s["感想"])
        })
    c_df = pd.DataFrame(c_rows)
    c_df["順位"] = c_df.groupby("区分")["得点"].rank(method="min", ascending=False).astype(int)

    # 5. 画面表示
    st.subheader("🥇 個人総合ランキング")
    st.table(p_df[p_df["順位"] <= 5][["順位", "制作者名", "総合得点", "ひとめ得点", "ぼれ得点", "ひとめ(1位/2位/3位)", "ぼれ(1位/2位/3位)"]])

    col_h, col_b = st.columns(2)
    with col_h:
        st.subheader("✨ ひとめpt 部門別TOP5")
        h_top = c_df[c_df["区分"] == "ひとめ"].sort_values("順位").head(5)
        st.table(h_top[["順位", "ID", "制作者", "得点", "1位票", "2位票", "3位票"]])
    with col_b:
        st.subheader("🔥 ぼれpt 部門別TOP5")
        b_top = c_df[c_df["区分"] == "ぼれ"].sort_values("順位").head(5)
        st.table(b_top[["順位", "ID", "制作者", "得点", "1位票", "2位票", "3位票"]])

    # 6. ダウンロード
    st.divider()
    csv_p = p_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("個人総合結果CSVをダウンロード", csv_p, "overall_results.csv", "text/csv")
    csv_c = c_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("作品別・部門別詳細CSVをダウンロード", csv_c, "creative_details.csv", "text/csv")