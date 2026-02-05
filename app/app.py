import streamlit as st
import pandas as pd
import re

# ページ設定
st.set_page_config(page_title="感想付き・ダブルランキング集計", layout="wide")

st.title("🏆 投票集計・ランキング発表システム")
st.write("「個人総合」と「作品単体」の2つの視点でランキングを自動作成します。")

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
    mapping_dict = {} # ID -> 名前
    id_to_type = {}   # ID -> "A" or "B"
    name_to_ids = {}  # 名前 -> {"A": id1, "B": id2}
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
        st.warning("⚠️ ID対応表がアップロードされていません。")
        ans = st.radio("このままIDのみで集計しますか？", ("選択してください", "はい", "いいえ"))
        if ans != "はい": st.stop()
        use_mapping = False

    # 3. 集計 & 感想抽出
    rank_cols = [c for c in vote_df.columns if re.search(r'[1-3１-３]位', c)]
    
    creator_stats = {} # 個人合計用
    id_stats = {}      # 作品単体用

    for _, row in vote_df.iterrows():
        for col in rank_cols:
            raw_id = normalize_id(row[col])
            if not raw_id: continue
            
            # 得点判定
            points = 3 if '1' in col or '１' in col else (2 if '2' in col or '２' in col else 1)
            
            # 感想の取得
            col_idx = vote_df.columns.get_loc(col)
            reason = str(row.iloc[col_idx + 1]).strip() if col_idx + 1 < len(vote_df.columns) else ""
            if reason == "nan" or not reason: reason = ""

            # --- 作品単体の集計 ---
            if raw_id not in id_stats:
                id_stats[raw_id] = {"得点": 0, "感想": []}
            id_stats[raw_id]["得点"] += points
            if reason: id_stats[raw_id]["感想"].append(reason)

            # --- 個人総合の集計 ---
            key = mapping_dict.get(raw_id, raw_id) if use_mapping else raw_id
            if key not in creator_stats:
                creator_stats[key] = {"合計": 0, "A_score": 0, "B_score": 0, "A_reasons": [], "B_reasons": []}
            
            creator_stats[key]["合計"] += points
            if use_mapping:
                work_type = id_to_type.get(raw_id, "不明")
                if work_type == "A":
                    creator_stats[key]["A_score"] += points
                    if reason: creator_stats[key]["A_reasons"].append(reason)
                elif work_type == "B":
                    creator_stats[key]["B_score"] += points
                    if reason: creator_stats[key]["B_reasons"].append(reason)

    # 4. データ整形
    # 4a. 作品別（クリエイティブ別）ランキング
    creative_rows = []
    for rid, data in id_stats.items():
        creator_name = mapping_dict.get(rid, "不明")
        work_type = id_to_type.get(rid, "-")
        creative_rows.append({
            "ID": rid,
            "制作者名": creator_name,
            "種別": work_type,
            "作品得点": data["得点"],
            "感想": f"【{rid}】への感想 : " + " / ".join(data["感想"]) if data["感想"] else ""
        })
    creative_df = pd.DataFrame(creative_rows)
    creative_df['順位'] = creative_df['作品得点'].rank(method='min', ascending=False).astype(int)
    creative_df = creative_df.sort_values(by=['順位', '作品得点'], ascending=[True, False]).reset_index(drop=True)

    # 4b. 個人総合ランキング
    overall_rows = []
    for name, data in creator_stats.items():
        ids = name_to_ids.get(name, {"A": "?", "B": "?"})
        overall_rows.append({
            "制作者名": name,
            "合計得点": data["合計"],
            "作品A得点": data["A_score"],
            "作品B得点": data["B_score"],
            "作品A感想": f"【{ids['A']}】への感想 : " + " / ".join(data["A_reasons"]) if data["A_reasons"] else "",
            "作品B感想": f"【{ids['B']}】への感想 : " + " / ".join(data["B_reasons"]) if data["B_reasons"] else ""
        })
    overall_df = pd.DataFrame(overall_rows)
    overall_df['順位'] = overall_df['合計得点'].rank(method='min', ascending=False).astype(int)
    overall_df = overall_df.sort_values(by=['順位', '合計得点'], ascending=[True, False]).reset_index(drop=True)

    # 5. 表示
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🥇 個人総合ランキング (TOP 5)")
        st.write("作品AとBの合計スコア")
        display_overall = overall_df.copy()
        display_overall["順位表示"] = display_overall["順位"].apply(decorate_rank)
        st.table(display_overall[display_overall['順位'] <= 5][["順位表示", "制作者名", "合計得点"]])

    with col2:
        st.subheader("🎬 作品別ランキング (TOP 5)")
        st.write("各動画単体のスコア")
        display_creative = creative_df.copy()
        display_creative["順位表示"] = display_creative["順位"].apply(decorate_rank)
        st.table(display_creative[display_creative['順位'] <= 5][["順位表示", "制作者名", "種別", "作品得点"]])

    # 6. ダウンロード
    st.divider()
    st.subheader("📥 全結果のダウンロード")
    
    # 総合結果CSV
    csv_overall = overall_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(label="1. 個人総合結果(詳細)を保存", data=csv_overall, file_name='overall_ranking.csv', mime='text/csv')
    
    # 作品別結果CSV
    csv_creative = creative_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(label="2. 作品別結果(詳細)を保存", data=csv_creative, file_name='creative_ranking.csv', mime='text/csv')