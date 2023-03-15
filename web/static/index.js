//Initialize the viewer widget with several custom options and mixins.
const viewer = new Cesium.Viewer('cesiumContainer', {
    animation: false,
    fullscreenButton: false,
    geocoder: false,
    homeButton: false,
    navigationHelpButton: false,
    navigationInstructionsInitiallyVisible: false,
    scene3DOnly: true,
    timeline: false,
    terrainProvider: Cesium.createWorldTerrain()
});
const scene = viewer.scene;
const globe = scene.globe;
var tileset = null;
var tiles = [];
var geojson = null;
var voxels = [];

// underground
scene.screenSpaceCameraController.enableCollisionDetection = false;
globe.translucency.frontFaceAlphaByDistance = new Cesium.NearFarScalar(
    400.0,
    0.0,
    800.0,
    1.0
);

setUIEventHandlers();

function uploadTiles(form) {
    setMessage('タイルデータをアンロードしています');
    clearTiles();
    setMessage('タイルデータをロードしています');
    fetch(
        './upload/tiles',
        {
            method: 'POST',
            body: new FormData(form),
        }
    ).then((response) =>
        {
            if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        }
    ).then((result) =>
        {
            console.log(result);
            if (result.status === 'OK') {
                loadTiles(result);
            } else {
                setMessage('3D都市モデルのロードに失敗しました。');
            }
        }
    );
}

function uploadVoxels(form) {
    setMessage('ボクセルデータをアンロードしています');
    clearVoxels();
    setMessage('ボクセルデータをロードしています');
    fetch(
        './upload/csv',
        {
            method: 'POST',
            body: new FormData(form),
        }
    ).then((response) =>
        {
            if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        }
    ).then((result) =>
        {
            console.log(result);
            if (result.status === 'OK') {
                loadVoxels(result);
            } else {
                setMessage('３次元空間IDボクセルのロードに失敗しました。');
            }
        }
    );
}

function clearTiles() {
    if (tileset) {
        scene.primitives.remove(tileset);
    }
    if (geojson) {
        viewer.dataSources.remove(geojson);
    }
    tileset = null;
    tiles = [];
    geojson = null;
    document.querySelector('#chk_tiles').checked = '';
    document.querySelector('#chk_tiles').disabled = true;
}

function clearVoxels() {
    for (let i = 0; i < voxels.length; i++) {
        viewer.entities.remove(voxels[i]);
    }
    voxels = [];
    document.querySelector('#chk_voxels').checked = '';
    document.querySelector('#chk_voxels').disabled = true;
}

function loadTiles(tiles_info) {
    if (tiles_info.url.endsWith('tile.json')) {
        loadTiles2D(tiles_info);
    } else if (tiles_info.url.endsWith('tileset.json')) {
        loadTiles3D(tiles_info);
    } else {
        alert('Invalid data');
    }
}

function loadTiles2D(tiles_info) {
    Cesium.GeoJsonDataSource.load(tiles_info.url, {
        fill: new Cesium.Color(0.3, 0.3, 0.3, 0.5),
        clampToGround: true
    }).then((__geojson) => {
        geojson = __geojson;
        viewer.dataSources.add(geojson);
        zoomToBounds(tiles_info.bbox);
        buildVoxelDescription2D();
        document.querySelector('#chk_tiles').checked = 'checked';
        document.querySelector('#chk_tiles').disabled = false;
    });
}

function loadTiles3D(tiles_info) {
    var _tileset = new Cesium.Cesium3DTileset({
        url: tiles_info.url,
    });
    _tileset.tileLoad.addEventListener(function(_tile) {
        tiles.push(_tile);
    });
    _tileset.readyPromise.then((__tileset) => {
        tileset = __tileset;
        scene.primitives.add(tileset);
        zoomToBounds(tiles_info.bbox);
        buildVoxelDescription3D();
        document.querySelector('#chk_tiles').checked = 'checked';
        document.querySelector('#chk_tiles').disabled = false;
    });
}

function loadVoxels(box_info) {
    const rects = box_info.data.rectangles;
    const boxes = box_info.data.boxes;
    const total = box_info.total;
    const loaded = box_info.loaded;

    if (total > loaded) {
        alert(`${total} 件中の ${loaded} 件を表示しています`);
    }

    loadVoxels2D(rects);
    loadVoxels3D(boxes);

    zoomToBounds(box_info.bbox);
    buildVoxelDescription2D();
    buildVoxelDescription3D();
    document.querySelector('#chk_voxels').checked = 'checked';
    document.querySelector('#chk_voxels').disabled = false;
}

function loadVoxels2D(rectangles) {
    if (!rectangles) {
        return;
    }
    for (let i = 0; i < rectangles.length; i++) {
        let coords = rectangles[i].rectangle;
        let sid = rectangles[i].sid;
        let gids = rectangles[i].gids;
        let rectangle = new Cesium.RectangleGraphics({
            coordinates: new Cesium.Rectangle(coords[0], coords[1], coords[2], coords[3]),
            material: new Cesium.Color(0.0, 0.5, 1.0, 0.5),
            outline: true,
            outlineColor: new Cesium.Color(0.5, 0.5, 1.0, 1.0),
            outlineWidth: 1.0
        });
        let voxel = viewer.entities.add({
            name: sid,
            rectangle: rectangle,
            properties: ['gml_ids']
        });
        voxel.gml_ids = gids;
        voxels.push(voxel);
    }
}

function loadVoxels3D(boxes) {
    if (!boxes) {
        return;
    }
    for (let i = 0; i < boxes.length; i++) {
        let center = boxes[i].center;
        let size = boxes[i].size;
        let sid = boxes[i].sid;
        let gids = boxes[i].gids;
        let box = new Cesium.BoxGraphics({
            dimensions: new Cesium.Cartesian3(size[0], size[1], size[2]),
            material: new Cesium.Color(0.0, 0.5, 1.0, 0.5),
            outline: true,
            outlineColor: new Cesium.Color(0.5, 0.5, 1.0, 1.0),
            outlineWidth: 1.0
        });
        let position = new Cesium.Cartesian3(center[0], center[1], center[2]);
        let voxel = viewer.entities.add({
            name: sid,
            position: position,
            box: box,
            properties: ['gml_ids']
        });
        voxel.gml_ids = gids;
        voxels.push(voxel);
    }
}

function setUIEventHandlers() {

    document.querySelector('#chk_tiles').addEventListener('change', ((ev) => {
        let visible = ev.target.checked;
        if (tileset) {
            tileset.show = visible;
        }
        if (geojson) {
            geojson.show = visible;
        }
    }));

    document.querySelector('#chk_voxels').addEventListener('change', ((ev) => {
        let visible = ev.target.checked;
        for (let i = 0; i < voxels.length; i++) {
            voxels[i].show = visible;
        }
    }));

}

function buildVoxelDescription2D() {
    if (voxels.length) {
        setMessage('属性情報を準備しています');
        if (geojson) {
            const features = {};
            for (let i = 0; i < geojson.entities._entities.length; i++) {
                let feature = geojson.entities._entities._array[i];
                let props = feature.properties.getValue();
                let gml_id = props['gml:id'] || props['gml_id'];
                if (gml_id) {
                    features[gml_id] = feature;
                }
            }
            for (let i = 0; i < voxels.length; i++) {
                let voxel = voxels[i];
                let description = '';
                for (let j = 0; j < voxel.gml_ids.length; j++) {
                    let gml_id = voxel.gml_ids[j];
                    let feature = features[gml_id];
                    if (!feature) {
                        continue;
                    }
                    let attributes = getAttributes2D(feature);
                    description += `
                        <table class="cesium-infoBox-defaultTable">
                        <tbody>
                        `;
                    for (let k = 0; k < attributes.length; k++) {
                        let attribute = attributes[k];
                        description += `
                            <tr><th>${attribute.name}</th><td>${attribute.value}</td></tr>
                        `;
                    }
                    description += `
                        </tbody>
                        </table>
                        <div class="space"></div>
                        `;
                }
                voxel.description = description;
                voxel._desc_set = true;
            }
        } else {
            for (let i = 0; i < voxels.length; i++) {
                let voxel = voxels[i];
                let description = `
                    <table class="cesium-infoBox-defaultTable">
                    <tbody>
                    `;
                for (let j = 0; j < voxel.gml_ids.length; j++) {
                    let gml_id = voxel.gml_ids[j];
                    description += `
                        <tr><th>gml:id</th><td>${gml_id}</td></tr>
                    `;
                description += `
                    </tbody>
                    </table>
                    <div class="space"></div>
                    `;
                }
                voxel.description = description;
            }
        }
    }
    setMessage(null);
}

function buildVoxelDescription3D() {
    if (voxels.length) {
        setMessage('属性情報を準備しています');
        if (tiles.length) {
            const features = {};
            for (let i = 0; i < tiles.length; i++) {
                let tile = tiles[i];
                for (let j = 0; j < tile.content.featuresLength; j++) {
                    let feature = tile.content.getFeature(j);
                    let attrs = feature.getProperty('attributes');
                    let gml_id = attrs['gml:id'] || attrs['gml_id'];
                    if (gml_id) {
                        features[gml_id] = feature;
                    }
                }
            }
            for (let i = 0; i < voxels.length; i++) {
                let voxel = voxels[i];
                let description = '';
                for (let j = 0; j < voxel.gml_ids.length; j++) {
                    let gml_id = voxel.gml_ids[j];
                    let feature = features[gml_id];
                    if (!feature) {
                        continue;
                    }
                    let attributes = getAttributes3D(feature);
                    description += `
                        <table class="cesium-infoBox-defaultTable">
                        <tbody>
                        `;
                    for (let k = 0; k < attributes.length; k++) {
                        let attribute = attributes[k];
                        description += `
                            <tr><th>${attribute.name}</th><td>${attribute.value}</td></tr>
                        `;
                    }
                    description += `
                        </tbody>
                        </table>
                        <div class="space"></div>
                        `;
                }
                voxel.description = description;
            }
        } else {
            for (let i = 0; i < voxels.length; i++) {
                let voxel = voxels[i];
                if (voxel._desc_set) {
                    continue;
                }
                let description = `
                    <table class="cesium-infoBox-defaultTable">
                    <tbody>
                    `;
                for (let j = 0; j < voxel.gml_ids.length; j++) {
                    let gml_id = voxel.gml_ids[j];
                    description += `
                        <tr><th>gml:id</th><td>${gml_id}</td></tr>
                    `;
                description += `
                    </tbody>
                    </table>
                    <div class="space"></div>
                    `;
                }
                voxel.description = description;
            }
        }
    }
    setMessage(null);
}

function zoomToBounds(bbox) {
    if (bbox.length == 4) {
        viewer.camera.flyTo({
            destination: Cesium.Rectangle.fromDegrees(
                bbox[0],
                bbox[1],
                bbox[2],
                bbox[3]
            )
        });
    } else if (bbox.length == 6) {
        let bsphere = Cesium.BoundingSphere.fromCornerPoints(
            Cesium.Cartesian3.fromDegrees(bbox[0], bbox[1], bbox[4]),
            Cesium.Cartesian3.fromDegrees(bbox[2], bbox[3], bbox[5])
        );
        viewer.camera.flyToBoundingSphere(bsphere);
    }
}

function setMessage(message) {
    const elm = document.querySelector('#message');
    elm.textContent = message ?? '';
    elm.style.visibility = message ? 'visible' : 'hidden';
}
