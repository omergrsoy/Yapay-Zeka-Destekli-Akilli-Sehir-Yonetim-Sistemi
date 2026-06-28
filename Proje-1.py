import os
import sys
import xml.etree.ElementTree as ET
import subprocess
if 'SUMO_HOME' in os.environ:
    araclar = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(araclar)
else:
    sys.exit("Lütfen 'SUMO_HOME' ortam değişkenini manuel tanımlayın.")
import traci

def ag_donustur(cozum, dizin):
    net_dosyasi = os.path.join(dizin, "Yenisehir_Proje-1-2.net.xml")
    prefix = os.path.join(dizin, "gecici_ag")
    decompile_cmd = f'netconvert -s "{net_dosyasi}" --plain-output-prefix "{prefix}" --no-warnings true'
    try:
        subprocess.run(decompile_cmd, shell=True, check=True)
    except Exception as e:
        print(f"Netconvert ağ dosyasını decompile ederken hata oluştu: {e}")
        return
    edg_dosyasi = f"{prefix}.edg.xml"
    nod_dosyasi = f"{prefix}.nod.xml"
    typ_dosyasi = f"{prefix}.typ.xml"
    degistiMi = False
    guncellemeler = {}
    
    try:
        edg_tree = ET.parse(edg_dosyasi)
        edg_root = edg_tree.getroot()
        
        for edge in edg_root.findall('edge'):
            yol_id = edge.get('id')
            if yol_id in cozum:
                cozumler = cozum[yol_id]
                hedef_kavsak_id = edge.get('to')

                if 'SERIT_ARTIR' in cozumler:
                    mevcut_serit = int(edge.get('numLanes', 1))
                    yeni_serit = mevcut_serit + 1
                    edge.set('numLanes', str(yeni_serit))
                    print(f"'{yol_id}' yolunun şerit sayısı {mevcut_serit}'den {yeni_serit}'e çıkarıldı.")
                    degistiMi = True
                    
                if 'TRAFIK_ISIGI' in cozumler and hedef_kavsak_id:
                    guncellemeler[hedef_kavsak_id] = "traffic_light"

                elif 'DONER_KAVSAK' in cozumler and hedef_kavsak_id:
                    guncellemeler[hedef_kavsak_id] = "roundabout"
                    
        nod_tree = ET.parse(nod_dosyasi)
        nod_root = nod_tree.getroot()
        
        for node in nod_root.findall('node'):
            node_id = node.get('id')
            if node_id in guncellemeler:
                yeni_tip = guncellemeler[node_id]
                node.set('type', yeni_tip)
                islem_adi = "Trafik Işığı" if yeni_tip == "traffic_light" else "Döner Kavşak"
                print(f"'{node_id}' kavşağına {islem_adi} entegre edildi.")
                degistiMi = True
                
        if degistiMi:
            edg_tree.write(edg_dosyasi, encoding='UTF-8', xml_declaration=True)
            nod_tree.write(nod_dosyasi, encoding='UTF-8', xml_declaration=True)
            
            recompile_cmd = f'netconvert -e "{edg_dosyasi}" -n "{nod_dosyasi}" -o "{net_dosyasi}" --tls.guess true --no-warnings true'
            if os.path.exists(typ_dosyasi): 
                recompile_cmd += f' -t "{typ_dosyasi}"'
            try:
                subprocess.run(recompile_cmd, shell=True, check=True)
                print("Harita yeniden oluşturuldu.")
            except subprocess.CalledProcessError:
                print("Netconvert haritayı derlerken bir sorun yaşadı.")
    except Exception as e:
        print(f"XML veya Derleme işlemi sırasında hata oluştu: {e}")

def simulasyonu_calistir(iterasyon_no):
    print(f"\n{'='*50}")
    print(f"DÖNGÜ: {iterasyon_no}")
    print(f"Simülasyon başlıyor...\n")
    script_dizini = os.path.dirname(os.path.abspath(__file__))
    sumo_config_dosyasi = os.path.join(script_dizini, "Yenisehir_Proje-1-2.sumocfg")
    sumoCmd = ["sumo-gui", "-c", sumo_config_dosyasi, "--time-to-teleport", "150", "--device.rerouting.probability", "1",
        "--ignore-route-errors", "true"
    ]
    traci.start(sumoCmd)
    adim = 0
    sorunlu_yollar_hafizasi = {}
    merkez_kavsak_yollari = ["BKapi", "CarsimAVM", "EfsaneKokorec", "Isik_Bufe", "Kajun", "Park"] 
    dar_sokaklar = ["PegemAkademi", "BIM", "PizzaArt", "SeverseDoner", "Xtreme", "Mountain", "T90", "Swallove", "Arabica"]
    print("Harita taranıyor...")
    MAKSIMUM_ADIM = 4000 
    
    while traci.simulation.getMinExpectedNumber() > 0 and adim < MAKSIMUM_ADIM:
        traci.simulationStep()
        if adim % 50 == 0:
            kalan_arac = traci.simulation.getMinExpectedNumber()
            print(f"Simülasyon Adımı: {adim/50} | Kalan/Beklenen Araç: {kalan_arac}   ", end="\r")
        if adim % 10 == 0:
            tum_yollar = traci.edge.getIDList()

            for yol_id in tum_yollar:
                if not yol_id.startswith(":"):
                    bekleyen_arac = traci.edge.getLastStepHaltingNumber(yol_id)

                    if bekleyen_arac >= 3:
                        serit_0 = yol_id + "_0"
                        try:
                            bekleme_suresi = traci.lane.getWaitingTime(serit_0)
                            doluluk_orani = traci.lane.getLastStepOccupancy(serit_0) * 100
                        except:
                            bekleme_suresi = 0
                            doluluk_orani = 0

                        if yol_id in sorunlu_yollar_hafizasi:
                            sorunlu_yollar_hafizasi[yol_id]['sure'] += 10

                            if bekleyen_arac > sorunlu_yollar_hafizasi[yol_id]['maks_kuyruk']:
                                sorunlu_yollar_hafizasi[yol_id]['maks_kuyruk'] = bekleyen_arac

                            if bekleme_suresi > sorunlu_yollar_hafizasi[yol_id]['maks_bekleme']:
                                sorunlu_yollar_hafizasi[yol_id]['maks_bekleme'] = bekleme_suresi
                        else:
                            aktif_serit_sayisi = traci.edge.getLaneNumber(yol_id)
                            sorunlu_yollar_hafizasi[yol_id] = {
                                'sure': 10, 
                                'maks_kuyruk': bekleyen_arac,
                                'maks_bekleme': bekleme_suresi,
                                'maks_doluluk': doluluk_orani,
                                'serit_sayisi': aktif_serit_sayisi 
                            }
        adim += 1
    print("\n Simülasyon tamamlandı.")
    traci.close()
    print("\n RAPOR")
    otomasyon_cozumleri = {}
    rapor_olusturuldu = False
    
    for yol_id, veri in sorunlu_yollar_hafizasi.items():
        time = veri['sure']
        maks_kuyruk = veri['maks_kuyruk']
        maks_bekleme = veri['maks_bekleme']
        doluluk = veri['maks_doluluk']
        serit_sayisi = int(veri['serit_sayisi']) 
        
        if time >= 40 or maks_bekleme > 120 or doluluk > 80:
            rapor_olusturuldu = True
            karar_listesi = []
            print(f"\n '{yol_id}' ID'li Yol (Bekleme: {maks_bekleme:.1f}sn | Kuyruk: {maks_kuyruk})")
            
            if yol_id in merkez_kavsak_yollari:
                print("Ana Merkez Kavşağı -> Trafik ışığı eklenecek.")
                karar_listesi.append('TRAFIK_ISIGI')
            elif yol_id in dar_sokaklar:
                print("Dar Bağlantı Sokağı -> Ağır vasıta (Kamyon/Otobüs) girişi yasaklanacak.")
                karar_listesi.append('AGIR_VASITA_YASAKLA')
            else:
                if serit_sayisi == 1:
                    print("Tek Şeritli Standart Yol -> Şerit yetersiz. Yola 1 şerit daha eklenecek.")
                    karar_listesi.append('SERIT_ARTIR')
                elif serit_sayisi >= 2 and maks_kuyruk > 10:
                    print("Çok Şeritli Ana Kavşak -> Döner kavşak eklenecek.")
                    karar_listesi.append('DONER_KAVSAK')
                
            if karar_listesi:
                otomasyon_cozumleri[yol_id] = karar_listesi
                
    if not rapor_olusturuldu:
        print("\n Haritada hiçbir tıkanıklık tespit edilmedi.")
        return False 
        
    if otomasyon_cozumleri:
        ag_donustur(otomasyon_cozumleri, script_dizini)
    return True 

if __name__ == "__main__":
    maksimum_iterasyon = 2
    for i in range(1, maksimum_iterasyon + 1):
        devam_et = simulasyonu_calistir(i)
        if not devam_et:
            print(f"\n SİSTEM {i}. İTERASYONDA TAMAMEN OPTİMİZE EDİLDİ!")
            break
        if i < maksimum_iterasyon:
            print("\n 2. Simülasyon başlatılıyor...\n")