python citygml2id.py ../examples/citygml/udx/bldg ../examples/citygml/udx/bldg --grid-type zfxy --grid-level 23 --interpolate --merge
python id2citygml.py ../examples/citygml/udx/bldg ../examples/citygml/udx/bldg citygml/udx/bldg --spatialid both
python citygml2id.py ../examples/citygml/udx/urf ../examples/citygml/udx/urf --grid-type zfxy --grid-level 20
python id2citygml.py ../examples/citygml/udx/urf ../examples/citygml/udx/urf citygml/udx/urf --spatialid both
python citygml2id.py ../examples/citygml/udx/urf/urf_yoto_sample.gml ../examples/citygml/udx/urf/spatialid/urf_yoto_sample_zl20_3D.csv --grid-type zfxy --extract --extrude -10.0 100.0
