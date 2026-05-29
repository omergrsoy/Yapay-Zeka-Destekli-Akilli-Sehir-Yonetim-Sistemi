import os
import sys
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    # 'SUMO_HOME' ortam değişkeni tanımlı değilse, kullanıcıya hata mesajı göster ve çıkış yap
    sys.exit("Lütfen 'SUMO_HOME' ortam değişkenini manuel tanımlayın.")
import traci
def main():
    # 1. Python dosyasının içindeki klasörün tam yolu
    script_dizini = os.path.dirname(os.path.abspath(__file__))
    # 2. Config dosyasının yolu bu klasörle birleşir
    sumo_config_dosyasi = os.path.join(script_dizini, "Yenisehir_Proje-1-2.sumocfg")
    # Simülasyon başlar
    sumoCmd = ["sumo-gui", "-c", sumo_config_dosyasi]
    traci.start(sumoCmd)
    print("Simülasyon Başladı!")
    step = 0
    sorunlu_yollar_hafizasi = {}
    merkez_kavsak_yollari = ["BKapi", "CarsimAVM", "EfsaneKokorec", "Isik_Bufe", "Kajun", "Park"] 
    dar_sokaklar = ["PegemAkademi", "BIM", "PizzaArt", "SeverseDoner", "Xtreme"]
    print("Harita taranıyor, analiz yapılıyor")
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        # Her 10 saniyede bir tarama
        if step % 10 == 0:
            tum_yollar = traci.edge.getIDList()
            for yol_id in tum_yollar:
                if not yol_id.startswith(":"):
                    bekleyen_arac = traci.edge.getLastStepHaltingNumber(yol_id)
                    if bekleyen_arac >= 3:
                        if yol_id in sorunlu_yollar_hafizasi:
                            sorunlu_yollar_hafizasi[yol_id]['sure'] += 10
                            if bekleyen_arac > sorunlu_yollar_hafizasi[yol_id]['maks_kuyruk']:
                                sorunlu_yollar_hafizasi[yol_id]['maks_kuyruk'] = bekleyen_arac
                        else:
                            sorunlu_yollar_hafizasi[yol_id] = {'sure': 10, 'maks_kuyruk': bekleyen_arac}
        step += 1
    # RAPORLAMA
    print("\n")
    print("Tıkanıklık ve Çözüm Önerileri")
    print("\n")
    rapor_olusturuldu = False
    for yol_id, veri in sorunlu_yollar_hafizasi.items():
        sure = veri['sure']
        maks_kuyruk = veri['maks_kuyruk']
        if sure >= 40:
            rapor_olusturuldu = True
            serit_sayisi = traci.edge.getLaneNumber(yol_id)
            print(f"\n '{yol_id}' ID'li yolda {sure} sn tıkanıklık! (Maksimum {maks_kuyruk} araç kuyruk oldu)")
            print(f"ÇÖZÜM ÖNERİSİ:")
            if yol_id in merkez_kavsak_yollari:
                print("Ana Merkez Kavşağı")
                print("Bu bölgedeki trafik hacmi çok yüksek. Akıllı Trafik Işığı (Aktif Faz Yönetimi) kurulmalı.")
                if maks_kuyruk > 15:
                    print("Kuyruk 15 aracı aştığı için, kavşak öncesi sağa dönüşler için 'Serbest Geçiş' cebi açılmalı.")
            elif yol_id in dar_sokaklar:
                print("Dar Bağlantı Sokağı")
                print("Bu yol çift yönlü trafiği kaldıramıyor. Yol 'Tek Yönlü' olarak yeniden düzenlenmeli.")
                print("Taksilerin ve ağır vasıtaların bu sokağa girişi kısıtlanmalı.")
            else:
                if serit_sayisi == 1:
                    print("Tek Şeritli Standart Yol")
                    print("Şerit sayısı yetersiz. Kavşak şerit sayısı 2'ye çıkarılmalı.")
                elif serit_sayisi >= 2 and maks_kuyruk > 10:
                    print("Çok Şeritli Ana Kavşak")
                    print("Geçiş üstünlüğü kuralları ihlal ediliyor veya yetersiz kalıyor.")
                    print("Kavşak 'Döner Kavşak' olarak değiştirilmeli.")
    if not rapor_olusturuldu:
        print("\nSimülasyon boyunca hiçbir bölgede tıkanıklık yok.")
    traci.close()
    print("Simülasyon Bitti ve TraCI bağlantısı kapatıldı.")
if __name__ == "__main__":
    main()