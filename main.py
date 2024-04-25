import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
import networkx as nx
from geopy.distance import great_circle
from tkinter import messagebox
import mysql.connector

# Veritabanı bağlantı bilgileri
config = {
    "user": "root",
    "password": "",
    "host": "localhost",
    "database": "test",
    "raise_on_warnings": True
}
try:
    db_conn = mysql.connector.connect(**config)
    cursor = db_conn.cursor()
except mysql.connector.Error as err:
    messagebox.showerror("Veritabanı Bağlantı Hatası", f"Veritabanına bağlanırken bir hata oluştu: {err}")
    exit(1)  # Veritabanı bağlantı hatası durumunda uygulamayı kapat

def fetch_car_models():
    """Veritabanından araç modellerini çeker ve bir liste olarak döndürür."""
    query = "SELECT model FROM araclar"
    cursor.execute(query)
    models = cursor.fetchall()
    return [model[0] for model in models]

def fetch_max_distance(model):
    """Seçilen araç modeline göre maksimum mesafeyi veritabanından çeker."""
    global cursor  # Global cursor kullanılıyor
    query = "SELECT max_distance FROM araclar WHERE model = %s"
    cursor.execute(query, (model,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        messagebox.showerror("Hata", "Model için maksimum mesafe bulunamadı.")
        return 0  # Bir hata oluşursa 0 döndür

def on_model_selected(event=None):  # event parametresi isteğe bağlı hale getirildi
    """Araç modeli seçildiğinde veya varsayılan model atandığında bu fonksiyon çağrılır."""
    global max_distance_with_full_charge
    selected_model = car_model_combobox.get()
    max_distance = fetch_max_distance(selected_model)
    max_distance_with_full_charge = max_distance
    print(f"Seçilen modelin maksimum mesafesi: {max_distance_with_full_charge}")


# Şehirler, şarj istasyonları ve koordinatları
cities = {
    'İstanbul': (41.0082, 28.9784),
    'Ankara': (39.9334, 32.8597),
    'Trabzon': (41.0027, 39.7168),
    'Ağrı': (39.7191, 43.0503),
    'Hatay': (36.2021, 36.1601),
    'Antalya': (36.8969, 30.7133),
    'İzmir': (38.4237, 27.1428),
}

charging_stations = {
    'Şarj İstasyonu 1': (39.7477, 37.0179),
    'Şarj İstasyonu 2': (39.7662, 30.5256),
    'Şarj İstasyonu 3': (36.8004, 34.6124),
    'Şarj İstasyonu 4': (39.6484, 27.8826),
}

# Tam şarjla aracın gidilebileceği maksimum mesafe (km)

max_distance_with_full_charge = 0


def find_path_with_charging(start_city, end_city, charge_percentage):
    nodes = {**cities, **charging_stations}
    G = nx.Graph()

    for node1, coord1 in nodes.items():
        for node2, coord2 in nodes.items():
            if node1 != node2:
                distance = great_circle(coord1, coord2).kilometers
                G.add_edge(node1, node2, weight=distance)

    max_distance = (charge_percentage / 100) * max_distance_with_full_charge
    shortest_path = nx.dijkstra_path(G, source=start_city, target=end_city, weight='weight')

    path_with_charging = [shortest_path[0]]
    current_charge_distance = max_distance

    for i in range(1, len(shortest_path)):
        distance = G[shortest_path[i - 1]][shortest_path[i]]['weight']
        if current_charge_distance - distance < 0:
            # Şarj için uygun bir şarj istasyonunu bul (bu örnekte basitleştirme yapıyoruz)
            # Gerçekte, en uygun şarj istasyonunu bulmak için ek mantık gerekebilir
            for station in charging_stations.keys():
                if station in shortest_path[:i]:
                    path_with_charging.append(station)  # En son geçilen şarj istasyonunu ekleyin
                    break
            current_charge_distance = max_distance
        current_charge_distance -= distance
        if shortest_path[i] not in path_with_charging:
            path_with_charging.append(shortest_path[i])

    return G, path_with_charging, {node: (lon, lat) for node, (lat, lon) in nodes.items()}


def on_find_path():
    start_city = start_var.get()
    end_city = end_var.get()
    try:
        charge_percentage = float(charge_var.get())
    except ValueError:
        messagebox.showerror("Hatalı Giriş", "Lütfen geçerli bir şarj durumu yüzdesi giriniz.")
        return

    if not (0 <= charge_percentage <= 100):
        messagebox.showerror("Hatalı Giriş", "Şarj durumu yüzdesi 0 ile 100 arasında olmalıdır.")
        return

    G, path_with_charging, pos = find_path_with_charging(start_city, end_city, charge_percentage)
    total_distance = nx.dijkstra_path_length(G, source=start_city, target=end_city, weight='weight')

    # Şarj yeterli mi kontrol et
    achievable_distance = (charge_percentage / 100) * max_distance_with_full_charge
    if achievable_distance >= total_distance:
        messagebox.showinfo("Yolculuk Mümkün", "Mevcut şarjınız varış noktasına gitmek için yeterli.")
    else:
        # En yakın şarj istasyonunu bul
        for station in charging_stations:
            station_distance = nx.dijkstra_path_length(G, source=start_city, target=station, weight='weight')
            if station_distance <= achievable_distance:
                path_with_charging.insert(1, station)
                break
        else:
            messagebox.showwarning("Yetersiz Şarj", "Hiçbir şarj istasyonuna ulaşacak kadar şarjınız yok.")
            return
    # GUI kapat
    root.destroy()

    # Yolu görselleştir
    plt.figure(figsize=(12, 10))

    nx.draw_networkx_nodes(G, pos, nodelist=cities.keys(), node_color='skyblue', node_size=500)
    nx.draw_networkx_nodes(G, pos, nodelist=charging_stations.keys(), node_color='yellow', node_size=700, node_shape='*')
    nx.draw_networkx_labels(G, pos, labels={node: node for node in pos.keys()}, font_color='darkblue')
    nx.draw_networkx_edges(G, pos, edge_color='gray')
    path_edges = list(zip(path_with_charging[:-1], path_with_charging[1:]))
    nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color='red', width=2)

    achievable_distance = (charge_percentage / 100) * max_distance_with_full_charge

    # İki şehir arasındaki mesafeyi ve aracın tam şarjla gidebileceği mesafeyi grafiğin en üstünde göster
    plt.text(0.5, 1.0, f"İki şehir arasındaki mesafe: {total_distance:.2f} km", fontsize=12, ha='center', va='center',
             transform=plt.gca().transAxes, bbox=dict(facecolor='yellow', alpha=0.6))
    plt.text(0.5, 1.05, f"Aracın %100 şarj ile gidilebileceği maksimum mesafe: {max_distance_with_full_charge} km",
             fontsize=12, ha='center', va='center', transform=plt.gca().transAxes,
             bbox=dict(facecolor='yellow', alpha=0.6))
    plt.text(0.5, 1.10, f"Aracın mevcut şarjıyla gidilebilecek mesafe: {achievable_distance:.2f} km", fontsize=12,
             ha='center', va='center', transform=plt.gca().transAxes, bbox=dict(facecolor='yellow', alpha=0.6))
    plt.text(0.5, 1.15, f"Başlangıç Şarjı: %{charge_percentage}",
             fontsize=12, ha='center', va='center', transform=plt.gca().transAxes,
             bbox=dict(facecolor='yellow', alpha=0.6))

    #plt.title(f"{start_city}'dan {end_city}'ye En Kısa Yol (Başlangıç Şarjı: %{charge_percentage})")
    plt.axis('off')
    plt.show()



# GUI oluştur
root = tk.Tk()
root.title("En Kısa Yol Bulucu (Şarj Durumu ile)")
root.configure(bg='#f0f0f0')  # Arka plan rengini ayarla

# Stil ayarları
style = ttk.Style()
style.theme_use('clam')
style.configure('TButton', font=('Arial', 10, 'bold'), background='#4CAF50')
style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
style.configure('TEntry', font=('Arial', 10))
style.configure('TCombobox', font=('Arial', 10))

start_var = tk.StringVar()
end_var = tk.StringVar()
charge_var = tk.StringVar()
car_model_var = tk.StringVar()

# Başlangıç Şehri
ttk.Label(root, text="Başlangıç Şehri:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
start_combobox = ttk.Combobox(root, textvariable=start_var, values=list(cities.keys()), width=30)
start_combobox.grid(row=0, column=1, padx=10, pady=5, sticky='ew')
start_combobox.current(0)

# Varış Şehri
ttk.Label(root, text="Varış Şehri:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
end_combobox = ttk.Combobox(root, textvariable=end_var, values=list(cities.keys()), width=30)
end_combobox.grid(row=1, column=1, padx=10, pady=5, sticky='ew')
end_combobox.current(1)

# Araç Modeli Seçimi
ttk.Label(root, text="Araç Modeli Seçiniz:").grid(row=2, column=0, padx=10, pady=5, sticky='w')
car_model_combobox = ttk.Combobox(root, textvariable=car_model_var, values=fetch_car_models(), width=30)
car_model_combobox.grid(row=2, column=1, padx=10, pady=5, sticky='ew')
car_model_combobox.current(0)  # Varsayılan olarak ilk modeli seç
car_model_combobox.bind("<<ComboboxSelected>>", on_model_selected)

# Aracın Şarj Durumu
ttk.Label(root, text="Aracın Şarj Durumu (%):").grid(row=3, column=0, padx=10, pady=5, sticky='w')
charge_entry = ttk.Entry(root, textvariable=charge_var, width=33)
charge_entry.grid(row=3, column=1, padx=10, pady=5, sticky='ew')

# Yolu Bul Butonu
find_path_button = ttk.Button(root, text="Yolu Bul", command=on_find_path)
find_path_button.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky='ew')

on_model_selected()  # İlk model seçimi için maksimum mesafeyi güncelle

root.mainloop()
