from sklearn.cluster import DBSCAN
import pandas as pd

def aplicar_dbscan(negocios, eps=0.01, min_samples=10):
    df = pd.DataFrame(negocios)
    coords = df[["lat", "lon"]].to_numpy()
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    df["cluster"] = db.labels_.astype(int)
    return df
