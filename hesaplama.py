import math

def hesapla_azimut_elevasyon(enlem, boylam, uydu_boylami):
    if enlem == 0.0:
        enlem = 0.0001
        
    enlem_rad = math.radians(enlem)
    delta_lambda_rad = math.radians(uydu_boylami - boylam)
    
    cos_gama = math.cos(enlem_rad) * math.cos(delta_lambda_rad)
    gama_rad = math.acos(cos_gama)
    
    a_ust = math.degrees(math.atan(abs(math.tan(delta_lambda_rad)) / math.sin(enlem_rad)))
    
    if uydu_boylami > boylam:
        azimut_derece = 180 - a_ust
    else:
        azimut_derece = 180 + a_ust
        
    sin_gama = math.sin(gama_rad)
    if sin_gama == 0.0:
        sin_gama = 0.0001
        
    elevasyon_rad = math.atan((cos_gama - 0.15127) / sin_gama)
    elevasyon_derece = math.degrees(elevasyon_rad)
    
    return round(azimut_derece, 2), round(elevasyon_derece, 2)

#görüntü işlem için 
KP_AZIMUT = 0.02
KP_ELEVASYON = 0.02

def piksel_hatasini_aciya_cevir(error_x, error_y):
    duzeltme_azimut = -error_x * KP_AZIMUT
    duzeltme_elevasyon = error_y * KP_ELEVASYON
    return duzeltme_azimut, duzeltme_elevasyon