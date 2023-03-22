const attribute_def_2d = [
    {name: 'properties/gml:id', title: 'gml:id'},
    {name: 'properties/gml_id', title: 'gml:id'},
    {name: 'properties/名称', title: '名称'},
    {name: 'properties/tran:function/0', title: 'tran:function'},
    {name: 'properties/luse:class', title: 'luse:class'},
    {name: 'properties/urf:disasterType', title: 'urf:disasterType'},
    {name: 'properties/urf:function/0', title: 'urf:function'}
];

const attribute_def_3d = [
    {name: 'attributes/gml:id', title: 'gml:id'},
    {name: '名称', title: '名称'},
    {name: 'attributes/bldg:class', title: 'bldg:class'},
    {name: 'attributes/bldg:usage/0', title: 'bldg:usage'},
    {name: 'attributes/brid:function/0', title: 'brid:function'},
    {name: 'attributes/frn:function/0', title: 'frn:function'},
    {name: 'attributes/tran:function/0', title: 'tran:function'},
    {name: 'attributes/veg:class', title: 'veg:class'},
    {name: 'attributes/wtr:function', title: 'wtr:function'}
];

function getAttributes2D(feature) {
    let attributes = [];
    for (let i = 0; i < attribute_def_2d.length; i++) {
        let components = attribute_def_2d[i].name.split('/');
        let node = feature;
        for (let j = 0; j < components.length; j++) {
            let component = components[j];
            if (component.match(/[0-9]+/)) {
                component = parseInt(component, 10);
            }
            if (j === 0) {
                node = node[component].getValue();
            } else {
                node = node[component];
            }
            if (!node) {
                break;
            }
        }
        if (node) {
            let name = attribute_def_2d[i].title || attribute_def_2d[i].name;
            let value = node;
            attributes.push({name: name, value: value});
        }
    }
    return attributes;
}

function getAttributes3D(feature) {
    let attributes = [];
    for (let i = 0; i < attribute_def_3d.length; i++) {
        let components = attribute_def_3d[i].name.split('/');
        let node = feature;
        for (let j = 0; j < components.length; j++) {
            let component = components[j];
            if (component.match(/[0-9]+/)) {
                component = parseInt(component, 10);
            }
            if (j === 0) {
                node = node.getProperty(component);
            } else {
                node = node[component];
            }
            if (!node) {
                break;
            }
        }
        if (node) {
            let name = attribute_def_3d[i].title || attribute_def_3d[i].name;
            let value = node;
            attributes.push({name: name, value: value});
        }
    }
    return attributes;
}
