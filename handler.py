# import pandas as pd
# import geopandas as gpd

# from shapely.geometry import Point
# from glob import glob
# from datetime import datetime
# from typing import List


def ETA40(event, context):
    nome_arquivo_ativando_evento = event["Records"][0]["s3"]["object"]["key"]

    print(nome_arquivo_ativando_evento)
