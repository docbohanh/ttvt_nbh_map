from flask import Flask, render_template, request, jsonify, send_file
import io
import json
import geopandas as gpd
import folium
import json
import hashlib

app = Flask(__name__)
TTVT_FILE = "ttvt.json"

def load_data():
    with open("px_data.json", "r", encoding="utf-8") as f:
        px_data = json.load(f)
    with open("ttvt.json", "r", encoding="utf-8") as f:
        ttvt = json.load(f)
    return px_data, ttvt

def thong_ke_theo_ttvt(ttvt_name):
    px_data, ttvt = load_data()
    
    if ttvt_name not in ttvt:
        raise ValueError(f"TTVT '{ttvt_name}' không tồn tại trong ttvt.json")
    
    list_px = ttvt[ttvt_name]
    tong_thue_bao = 0.0
    tong_dien_tich = 0.0
    tong_dan_so = 0

    for item in px_data:
        if item["ten"] in list_px:
            tong_thue_bao += float(item["thue_bao_quy_đoi"])
            tong_dien_tich += float(item["dien_tich"])
            tong_dan_so += int(item["dan_so"])

    return tong_thue_bao, tong_dien_tich, tong_dan_so


def load_ttvt():
    with open(TTVT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_color(name):
    hash_object = hashlib.md5(name.encode("utf-8"))
    hex_digest = hash_object.hexdigest()
    return f"#{hex_digest[:6]}"

GDF = gpd.read_file("nbh.geojson")
GDF = GDF.to_crs(epsg=4326)

@app.route("/")
def index():
    TTVT_DATA = load_ttvt()
    center = GDF.geometry.unary_union.centroid

    # Define your bounding box coordinates
    bounds_sw = [19.190684, 106.903212]  # [south_lat, west_lng]
    bounds_ne = [21.292334, 105.303267]  # [north_lat, east_lng]
    m = folium.Map(
        location=[center.y, center.x],
        zoom_start=11,
        min_zoom=9,
        max_bounds=True,  # Enable max bounds
        control_scale=False,
        tiles=None,
        zoom_control=False,
        attribution_control=False
    )
    folium.TileLayer(
        tiles='https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png',
        attr='&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>',
        name='Blank',
        control=False
    ).add_to(m)
    # Set max bounds for pan and zoom
    m.options['maxBounds'] = [bounds_sw, bounds_ne]
    m.options['minZoom'] = 9
    m.options['maxZoom'] = 18

    legend_items = []

    for kv_name, xa_list in sorted(TTVT_DATA.items()):
        gdf_sub = GDF[GDF["ten_xa"].isin(xa_list)]
        if gdf_sub.empty:
            continue


        tong_thue_bao, tong_dien_tich, tong_dan_so = thong_ke_theo_ttvt(kv_name)

        color = generate_color(kv_name)

        # Add to legend
        legend_items.append(f"""
        <tr>
            <td><span style="display:inline-block;width:18px;height:18px;background:{color};border:1px solid #333;border-radius:3px;margin-right:6px;"></span></td>
            <td><b>{kv_name}</b>&nbsp&nbsp&nbsp&nbsp&nbsp</td>
            <td>{int(tong_thue_bao):,}</td>
            <td>{tong_dien_tich:.2f} km²&nbsp&nbsp&nbsp</td>
            <td>{tong_dan_so:,}</td>
        </tr>
        """)

        # fg = folium.FeatureGroup(name=kv_name, show=True)
        fg = folium.FeatureGroup(name=f"{kv_name}", show=True)


        kv_centroid = gdf_sub.unary_union.centroid
        folium.Marker(
            [kv_centroid.y, kv_centroid.x],
            icon=folium.DivIcon(html=f"""
        <div style='text-align:center; min-width:250px;'>
        <div style='font-size:24px; font-weight:700; color:white;
                    text-shadow:-2px -2px 0 {color},2px -2px 0 {color},
                                -2px 2px 0 {color},2px 2px 0 {color};'>
            {kv_name}
        </div>
        <div style='font-size:13px; font-weight:600; color:red;
                    text-shadow:-1px -1px 0 #fff,1px -1px 0 #fff,
                                -1px 1px 0 #fff,1px 1px 0 #fff;'>
            TBQĐ: {int(tong_thue_bao):,}
        </div>
        <div style='font-size:13px; font-weight:600; color:red;
                    text-shadow:-1px -1px 0 #fff,1px -1px 0 #fff,
                                -1px 1px 0 #fff,1px 1px 0 #fff;'>
            DT: {tong_dien_tich:.2f} km²
        </div>
        <div style='font-size:13px; font-weight:600; color:red;
                    text-shadow:-1px -1px 0 #fff,1px -1px 0 #fff,
                                -1px 1px 0 #fff,1px 1px 0 #fff;'>
            DS: {tong_dan_so:,}
        </div>
        </div>
        """)
        ).add_to(fg)

        for _, row in gdf_sub.iterrows():
            tooltip = f"<b>Xã/Phường:</b> {row.get('ten_xa','')}<br><b>Khu vực TTVT:</b> {kv_name}<br>"
            for field, label in [("sap_nhap","Sáp nhập"),("dtich_km2","Diện tích (km²)"),
                                 ("dan_so","Dân số"),("matdo_km2","Mật độ (ng/km²)")]:
                val = row.get(field)
                if val not in [None, ""]:
                    tooltip += f"<b>{label}:</b> {val}<br>"

            folium.GeoJson(
                data=row["geometry"].__geo_interface__,
                tooltip=folium.Tooltip(tooltip, sticky=True),
                style_function=lambda x, color=color: {
                    "fillColor": color,
                    "color": "black",
                    "weight": 0.5,
                    "fillOpacity": 0.8,
                },
                highlight_function=lambda x: {
                    "color": "blue",
                    "weight": 2,
                    "fillOpacity": 0.9,
                }
            ).add_to(fg)

            centroid = row["geometry"].centroid
            folium.Marker(
                [centroid.y, centroid.x],
                icon=folium.DivIcon(html=f"""
                <div style='font-size:14px; font-weight:500; color:black;
                    text-shadow:-1px -1px 0 #fff,1px -1px 0 #fff,-1px 1px 0 #fff,1px 1px 0 #fff;'>
                    {row['ten_xa']}
                </div>""")
            ).add_to(fg)

        fg.add_to(m)

    # Add legend HTML
    legend_html = f"""
    <div style="
        position: fixed; 
        top: 10px; left: 10px; z-index: 9999; 
        background: white; padding: 12px 18px; 
        border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.2); 
        font-size: 14px; max-height: 60vh; overflow-y: auto;">      
      <table style="border-collapse:collapse;">
        <thead>
          <tr>
            <th></th>
            <th style='text-align:left;'>Chú giải</th>
            <th style='text-align:center;padding:8px 8px;'>TBQĐ</th>
            <th style='text-align:center;padding:8px 8px;'>Diện tích</th>
            <th style='text-align:center;padding:8px 8px;'>Dân số</th>
          </tr>
        </thead>
        <tbody>
          {''.join(legend_items)}
        </tbody>
      </table>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl(collapsed=False).add_to(m)
    return render_template("index.html", map_html=m._repr_html_(), kv_keys=list(TTVT_DATA.keys()), default_ttvt=json.dumps(TTVT_DATA))

@app.route("/update_ttvt", methods=["POST"])
def update_ttvt():
    data = request.get_json()
    with open(TTVT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify({"status": "success"})

@app.route("/export_ttvt_json")
def export_ttvt_json():
    with open(TTVT_FILE, "r", encoding="utf-8") as f:
        data = f.read()
    return send_file(
        io.BytesIO(data.encode("utf-8")),
        mimetype="application/json",
        as_attachment=True,
        download_name="ttvt.json"
    )

if __name__ == "__main__":
    app.run(debug=True, port=8386)

