try:
    import unzip_requirements
except ImportError:
    pass

import boto3
import os
import io
import time
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from datetime import datetime
from typing import List


def bacias(event, context):
    nome = event["Records"][0]["s3"]["object"]["key"].split("/")[0]

    time.sleep(10)

    dias = 0
    numero_modelo = 0

    if "Eta40" in nome:
        nome_arquivo = "ETA40_p"
        dias = 10
        numero_modelo = 3
    else:
        dias = 14
        if "Gefs50" in nome:
            nome_arquivo = "GEFS_p"
            numero_modelo = 2
        else:
            nome_arquivo = "ECMWF_p"
            numero_modelo = 1

    session = boto3.Session(
        aws_access_key_id=os.environ.get("ACCESS_KEY"),
        aws_secret_access_key=os.environ.get("ACCESS_SECRET"),
        region_name=os.environ.get("REGION"),
    )

    s3 = session.resource("s3")

    my_bucket = s3.Bucket("bucket-docs-nodejs")

    arquivos = []
    list: List = []
    dateList: List = []
    precData: List = []
    modelo: List = []
    bacias: List = []

    for my_bucket_object in my_bucket.objects.all():
        if (
            nome_arquivo in my_bucket_object.key
            and "precipitacao" not in my_bucket_object.key
        ):
            arquivos.append(my_bucket_object.key)
            date_from_files = (
                my_bucket_object.key.split("{}/{}".format(nome, nome_arquivo))[
                    1
                ]
                .split(".dat")[0]
                .split("a")[1]
            )

            dateFormat = "{}/{}/{}".format(
                date_from_files[:2], date_from_files[2:4], date_from_files[4:6]
            )

            dateList.append(dateFormat)

            body = my_bucket_object.get()["Body"].read()

            list.append(
                pd.read_table(
                    io.BytesIO(body),
                    sep="\s+",
                    header=None,
                    names=["lon", "lat", "prec"],
                )
            )

    for i in range(len(arquivos)):
        list[0].loc[:, dateList[i]] = list[i].loc[:, "prec"]

    dados = list[0]

    sinMap = gpd.read_file("maps/Bacias/SIN/Contorno_Bacias_rev2.shp")

    x = zip(dados.lon, dados.lat)
    geometry = [Point(x) for x in zip(dados.lon, dados.lat)]
    dateArray = dateList
    geo_dados = gpd.GeoDataFrame(dados, crs=sinMap.crs, geometry=geometry)

    modelo.clear()
    for i in range(len(sinMap)):
        modelo.append(
            pd.DataFrame(
                geo_dados[geo_dados["geometry"].within(sinMap.iloc[i].geometry)]
            )
        )

    precData.clear()
    for i in range(len(sinMap)):
        for j in range(len(dateArray)):
            precData.append(modelo[i][dateArray[j]].mean())

    precData = [precData[i : i + dias] for i in range(0, len(precData), dias)]

    dateArray = [
        (datetime.strptime(dateArray[i], "%d/%m/%y")).strftime("%Y/%m/%d")
        for i in range(len(dateArray))
    ]

    bacias.clear()
    for i in range(len(sinMap)):
        df_Modelo = pd.DataFrame(dateArray)
        df_Modelo["1"] = (datetime.today()).strftime("%Y/%m/%d")
        df_Modelo["2"] = numero_modelo
        df_Modelo["3"] = precData[i]
        df_Modelo["4"] = sinMap["Nome_Bacia"][i]
        bacias.append(df_Modelo)

    endData = pd.concat(bacias).reset_index(drop=True)

    csv_buffer = io.StringIO()

    endData.to_csv(csv_buffer, header=False, index=False)

    s3.Object("bucket-docs-nodejs", "{}/{}.csv".format(nome, nome)).put(
        Body=csv_buffer.getvalue()
    )

    print(nome, nome_arquivo, dias, numero_modelo)
