# 令和4年度　デジタル庁「デジタルツイン構築に向けた3D都市モデルの整備に関する調査研究」の成果物

## 概要

「3D都市モデル標準製品仕様書 第2.3版」準拠の3D都市モデルから「空間ID」を自動生成するためのツールです。

## 「PLATEAUのための空間ID生成ツール」について
令和4年度のデジタル庁「デジタルツイン構築に向けた3D都市モデルの整備に関する調査研究」において、人・機械が一意に空間を特定するための3次元グリッド（ボクセル）識別子である「空間ID」の実現・普及に貢献することを目的に、3次元の地理空間情報として中心的役割を担う「3D都市モデル」から「空間ID」を自動生成するツールを開発しました。
このツールは、二つのツールによって構成されています。
①空間IDを付与した3D都市モデル生成ツール：3D都市モデルに対し「空間ID」を自動付与するツール
②空間IDのメタデータ生成ツール：「空間ID」のメタデータに3D都市モデルの持つ属性情報を自動付与するツール

## 利用手順

### インストール方法

#### 事前準備

対応OSは以下の通りです。

- Windows
- macOS
- Linux

以下のソフトウェアをインストールしておいてください。

- Python 3.9
- Google Chrome または Microsoft Edge （ビューアを利用する場合）

#### コマンド部

空間IDを付与した3D都市モデル生成ツール、空間IDのメタデータ生成ツールのコマンド部のインストール手順は以下の通りです。

1. コマンドプロンプト（Windows）またはターミナル（macOS / Linux）を起動し、ツールのディレクトリに移動します。

    Windows の場合

        > cd command

    macOS / Linux の場合

        $ cd command

2. Python 仮想環境を作成し有効化します。

    Windows の場合

        > python -m venv .venv
        > .venv\Scripts\Activate

    macOS / Linux の場合

        $ python3 -m venv .venv
        $ source .venv/bin/activate

    ※ コマンド内の`.venv` は任意の名前に変更可能です。

3. Python 仮想環境に依存ライブラリをインストールします。

    Windows	の場合

        > pip install -r requirements.txt

	macOS / Linux の場合

    	$ pip install -r requirements.txt

#### ビューア部

空間IDのメタデータ生成ツールのビューア部のインストール手順は以下の通りです。

1. コマンドプロンプト（Windows）またはターミナル（macOS / Linux）を起動し、ツールのディレクトリに移動します。

    Windows の場合

        > cd web

    macOS / Linux の場合

        $ cd web

2. Python 仮想環境を作成し有効化します。

    Windows の場合

        > python -m venv .venv
        > .venv\Scripts\Activate

    macOS / Linux の場合

        $ python3 -m venv .venv
        $ source .venv/bin/activate

    ※ コマンド内の`.venv` は任意の名前に変更可能です。

3. Python 仮想環境に依存ライブラリをインストールします。

    Windows	の場合

        > pip install -r requirements.txt

	macOS / Linux の場合

    	$ pip install -r requirements.txt

4. 座標変換に必要なファイルをダウンロードします。

    Windows	の場合

        > pyproj sync --file us_nga_egm96_15.tif

	macOS / Linux の場合

    	$ pyproj sync --file us_nga_egm96_15.tif

### 使い方

#### 空間IDを付与した3D都市モデル生成ツール

1. コマンドプロンプト（Windows）またはターミナル（macOS / Linux）を起動し、ツールのディレクトリに移動します。

    Windows の場合

        > cd command

    macOS / Linux の場合

        $ cd command

2. Python 仮想環境を有効化します。

    Windows の場合

        > .venv\Scripts\Activate

    macOS / Linux の場合

        $ source .venv/bin/activate

3. CityGML から 地物ID（gml_id）と空間IDのペアリストを生成し CSV 出力します。

    Windows の場合

        > python citygml2id.py [コマンド引数]

    macOS / Linux の場合

        $ python citygml2id.py [コマンド引数]

    コマンド引数は以下の通りです。

    引数 | 説明 | 値 | デフォルト値
    --- | --- | --- | ---
    input_file_or_dir | CityGMLのファイルのパス（`*.gml`）または上位ディレクトリのパス | | |
    output_file_or_dir | 地物IDと空間IDのペアリストのファイルのパス（`*.csv`）または上位ディレクトリのパス | | |
    --lod | 処理するジオメトリの最大LOD | `1`, `2`, `3` | `3` |
    --grid-type | グリッドタイプ | `zfxy` | `zfxy` |
    --grid-level | グリッドのズームレベル | | `20` |
    --grid-size | グリッドのサイズ。x y z の順に指定。x のみ指定した場合は y z にも同じ値を適用。将来拡張用。 | | |
    --grid-crs | グリッドの座標参照系のEPSG番号。将来拡張用。 | | |
    --id | IDフィルタ。処理するデータを絞り込む際に gml:id の値を複数指定可能。 | | |
    --extract | 空間IDが付与された CityGML から、空間IDを抽出し、CSVへ出力する場合に指定。 | | |
    --extrude | ２次元データに付与する高さの最小値と最大値（単位：m）。--extract オプション指定時のみ有効。 | | |
    --interpolate | 立体（Solid）内側の空洞をボクセルで埋める場合に指定。Solid形状を持つ「Building（建築物）」「CityFurniture（都市設備）」「Vegetation（植生）」を空間IDに変換する際に使用するオプション。 | | |
    --merge | 上位の空間IDに統合（最適化）する場合に指定。 | | |
    --debug | デバッグログ出力および一時ファイル保持を有効にする場合に指定。 | | |
    -h | 使い方を表示。 | | |

4. CityGML および 地物ID（gml_id）と空間IDのペアリストから空間IDが付与されたCityGMLを生成します。

    Windows の場合

        > python id2citygml.py [コマンド引数]

    macOS / Linux の場合

        $ python id2citygml.py [コマンド引数]

    コマンド引数は以下の通りです。

    引数 | 説明 | 値 | デフォルト値
    --- | --- | --- | ---
    citygml_file_or_dir | CityGMLのファイルのパス(*.gml)または上位ディレクトリのパス | | |
    id_file_or_dir | 地物ID-空間IDペアリストのファイルのパス(*.csv)または上位ディレクトリのパス | | |
    output_file_or_dir | 空間IDを付与した CityGML のファイルのパス(*.gml)または上位ディレクトリのパス | | |
    --spatialid | 空間IDの付与方法　| `embedding`: CityGMLファイルに空間IDを直接付与 <br/> `reference`: 地物ID-空間IDペアリスト（CSVファイル）への相対パスを記録⇒CityGMLファイルへの空間IDの直接付与は行わず、外部ファイル参照のみで空間IDと紐付けする場合に使用 <br/> `both`: CityGMLファイルへの空間ID直接付与とCSVファイルへの相対パス記録の両者を実行 | `both` |
    -h | 使い方を表示 | | |

5. 使用例1: ファイルを指定し、citygml2id.pyを実行する

        $ python citygml2id.py ../examples/citygml/udx/bldg/building_sample.gml ../examples/citygml/udx/bldg/spatialid/building_sample_zl23_merged.csv --grid-type zfxy --grid-level 23 --interpolate --merge

    - 入力：building_sample.gml【3D都市モデル(CityGML)】
    - 出力：building_sample_zl23_merged.csv
    - グリッドタイプ：ZFXY
    - 基準（最大）ズームレベル：23
    - 空洞部の空間ID生成：実施
    - ズームレベル最適化：実施

    ※ [examplesディレクトリ](examples)のサンプルデータで動作を確認できます。

6. 使用例2: フォルダに対し、citygml2id.pyを実行（一括処理）する

        $ python citygml2id.py ../examples/citygml/udx/bldg ../examples/citygml/udx/bldg --grid-type zfxy --grid-level 23 --interpolate --merge
        $ python citygml2id.py ../examples/citygml/udx/urf ../examples/citygml/udx/urf --grid-type zfxy --grid-level 20

    - 入力：bldgフォルダ（建築物）とurfフォルダ（都市計画決定情報）
    - 出力：gmlファイルが存在するフォルダ直下にspatialidフォルダを生成しCSVファイルを格納
    - グリッドタイプ：ZFXY
    - 基準（最大）ズームレベル：bldgフォルダに対しては23、urfフォルダに対しては20
    - 空洞部の空間ID生成：Solid形状の建築物にのみ実施

    ※ [examplesディレクトリ](examples)のサンプルデータで動作を確認できます。

7. 使用例3: ファイルを指定し、id2citygml.pyを実行する

        $ python id2citygml.py ../examples/citygml/udx/bldg/building_sample.gml ../examples/citygml/udx/bldg/spatialid/building_sample_zl23_merged.csv ../examples/citygml/udx/bldg/building_sample.gml --spatialid both

    - 入力：building_sample.gml
    - 地物IDと空間IDのペアリスト（CSV）：building_sample_zl23_merged.csv
    - 出力：building_sample.gml（ファイルを更新）
    - 空間IDの付与方法：CityGMLへの直接付与と外部ファイル参照（相対パス埋め込み）の両方

    ※ examplesディレクトリのサンプルデータで動作を確認できます。事前に使用例1又は使用例2を実行しておいてください。

8. 使用例4: フォルダに対し、id2citygml.pyを実行（一括処理）する

        $ python id2citygml.py ../examples/citygml/udx/bldg ../examples/citygml/udx/bldg ../examples/citygml/udx/bldg --spatialid both
        $ python id2citygml.py ../examples/citygml/udx/urf ../examples/citygml/udx/urf ../examples/citygml/udx/urf --spatialid both

    - 入力：bldgフォルダ（建築物）とurfフォルダ（都市計画決定情報）
    - 地物IDと空間IDのペアリスト（CSV）：bldgフォルダとurfフォルダ内にあるspatialidフォルダ
    - 出力：bldgフォルダとurfフォルダ（フォルダ内のcitygmlファイルを更新）
    - 空間ID付与方法：CityGMLへの直接付与と外部ファイル参照（相対パス埋め込み）の両方

    ※ [examplesディレクトリ](examples)のサンプルデータで動作を確認できます。なお、使用例2を事前に実行しておいてください。

#### 空間IDのメタデータ生成ツール

##### コマンド部

1. コマンドプロンプト（Windows）またはターミナル（macOS / Linux）を起動し、ツールのディレクトリに移動します。

    Windows の場合

        > cd command

    macOS / Linux の場合

        $ cd command

2. Python 仮想環境を有効化します。

    Windows の場合

        > .venv\Scripts\Activate

    macOS / Linux の場合

        $ source .venv/bin/activate

3. 空間IDが付与された CityGML から 地物ID（gml_id）と空間IDのペアリストを CSV 出力します。

    Windows の場合

        > python citygml2id.py [コマンド引数]

    macOS / Linux の場合

        $ python citygml2id.py [コマンド引数]

    コマンド引数は以下の通りです。

    引数 | 説明 | 値 | デフォルト値
    --- | --- | --- | ---
    input_file_or_dir | CityGMLのファイルのパス（`*.gml`）または上位ディレクトリのパス | | |
    output_file_or_dir | 地物IDと空間IDのペアリストのファイルのパス（`*.csv`）または上位ディレクトリのパス | | |
    --lod | 処理するジオメトリの最大LOD | `1`, `2`, `3` | `3` |
    --grid-type | グリッドタイプ | `zfxy` | `zfxy` |
    --grid-level | グリッドのズームレベル | | `20` |
    --grid-size | グリッドのサイズ。x y z の順に指定。x のみ指定した場合は y z にも同じ値を適用。将来拡張用。 | | |
    --grid-crs | グリッドの座標参照系のEPSG番号。将来拡張用。 | | |
    --id | IDフィルタ。処理するデータを絞り込む際に gml:id の値を複数指定可能。 | | |
    --extract | 空間IDが付与された CityGML から、空間IDを抽出し、CSVへ出力する場合に指定。 | | |
    --extrude | ２次元データに付与する高さの最小値と最大値（単位：m）。--extract オプション指定時のみ有効。 | | |
    --interpolate | 立体（Solid）内側の空洞をボクセルで埋める場合に指定。Solid形状を持つ「Building（建築物）」「CityFurniture（都市設備）」「Vegetation（植生）」を空間IDに変換する際に使用するオプション。 | | |
    --merge | 上位の空間IDに統合（最適化）する場合に指定。 | | |
    --debug | デバッグログ出力および一時ファイル保持を有効にする場合に指定。 | | |
    -h | 使い方を表示。 | | |

4. 使用例5：2次元の空間ID（地理院タイル(XYZタイル)）が付与されたCityGMLファイルから空間IDを抽出し、3次元の空間ID（ZFXYタイル）を生成する

        $python citygml2id.py ../examples/citygml/udx/urf/urf_yoto_sample.gml ../examples/citygml/udx/urf/spatialid/urf_yoto_sample_zl20_3D.csv --grid-type zfxy --extract --extrude -10.0 100.0

    - 入力：urf_yoto_sample.gml
    - 出力：urf_yoto_sample_zl20_3D.csv
    - 空間IDを生成する標高値の範囲：-10mから100m

    ※ [examplesディレクトリ](examples)のサンプルデータで動作を確認できます。事前に使用例2と使用例4を実行しておいてください。

##### ビューア部

※ 本ドキュメントでは開発サーバを用いた手順に限定します。運用環境では Apache や Nginx 等の Web サーバと mod_wsgi や uwsgi 等の WSGI 準拠ミドルウェアを組み合わせてデプロイすることを推奨いたします。

1. コマンドプロンプト（Windows）またはターミナル（macOS / Linux）を起動し、ツールのディレクトリに移動します。

    Windows の場合

        > cd web

    macOS / Linux の場合

        $ cd web

2. Python 仮想環境を有効化します。

    Windows の場合

        > .venv\Scripts\Activate

    macOS / Linux の場合

        $ source .venv/bin/activate

3. 開発サーバを起動します

    Windows の場合

    	> flask --app server run

    macOS / Linux の場合

        $ flask --app server run

4. Webブラウザでビューアのトップページを開きます。URLは以下の通りです。

    http://127.0.0.1:5000

    ![](resources/viewer01.png)

5. データアップロード

    3D都市モデル、空間IDの順にアップロードします。

    ![](resources/viewer02.png)

6. データ確認

    チェックボックスで3D都市モデルや空間IDの表示を切り替えることができます。

    ![](resources/viewer03.png)

    3D都市モデルや空間ID（ボクセル）をクリックすると属性情報が表示されます。

    ![](resources/viewer04.png)

    ※ 3D都市モデル、空間IDの順にアップロードした場合、空間IDのメタデータに3D都市モデルの属性情報が付与されます。

    ※ ビューアで表示する3D都市モデルは、FME Hubで公開されているFMEワークスペース[PLATEAU2可視化用データ変換](https://hub.safe.com/?page=1&page_size=10&order=relevance&query=plateau)によって変換されたCesium 3D Tiles データセット (3Dモデル) または Mapbox Vector Tile (MVT) データセット (2Dポリゴン)を使用します。JSON属性にgml:idが記録されていない場合は、このワークスペースを編集し出力してください。

#### 使用例6：バッチファイルによる実行

バッチファイルを用意し複数のコマンドを連続処理することができます。
[examplesディレクトリ](examples)にサンプルデータ（建築物と用途地域）と、バッチファイルのサンプルを用意しています。
ツールをセットアップしたcommandフォルダ直下で、Python仮想環境を有効化し、[../examples/example.bat](examples/example.bat)を実行してください。

※ 使用例2、使用例4及び使用例5を連続して実行するバッチファイルです。

## ライセンス

* ソースコードおよび関連ドキュメントの著作権は国土交通省に帰属します。
* 本ドキュメントは[Project PLATEAUのサイトポリシー](https://www.mlit.go.jp/plateau/site-policy/)（CCBY4.0および政府標準利用規約2.0）に従い提供されています。

## 注意事項

* 本リポジトリは参考資料として提供しているものです。動作保証は行っておりません。
* 予告なく変更・削除する可能性があります。
* 本リポジトリの利用により生じた損失及び損害等について、国土交通省はいかなる責任も負わないものとします。

## 参考資料

* （近日公開）技術検証レポート: https://www.mlit.go.jp/plateau/libraries/technical-reports/
