# 🏠 Plan MVP - Analyse des Toitures

## 📋 Vue d'ensemble

**Objectif :** Développer un système de détection d'état des toitures pour améliorer le scoring d'abandon de fincas.

**Approche :** Entraînement d'un modèle YOLO custom sur 200 fincas annotées manuellement, puis test sur 400 fincas restantes.

## 🎯 Critères d'Analyse

### **3 Classes d'État de Toiture**

| Classe | Score | Critères |
|--------|-------|----------|
| **🏠 roof_good** | 4 points | Toiture intacte, couleurs vives, pas de dégradation |
| **🏠 roof_medium** | 2 points | Légères dégradations, couleurs ternies, quelques tuiles manquantes |
| **🏠 roof_bad** | 0 points | Dégradations importantes, holes, végétation dense |

## 📊 Système de Scoring Mis à Jour (24 points)

### **Nouveau Système avec Toitures**

| Critère | Points | Source de Données | Description |
|---------|--------|-------------------|-------------|
| **🚗 Présence Voitures** | 5 | Roboflow API | Détection YOLO directe |
| **🏠 État Toiture** | 4 | **NOUVEAU** - Modèle custom | Détection état toiture |
| **📅 Création Cadastrale** | 5 | Données cadastrales espagnoles | Date officielle de création |
| **🌿 Entretien Végétation** | 4 | NDVI Sentinel-2 | Variation sur 6 mois |
| **📡 Activité Radar** | 3 | Sentinel-1 VV | Backscatter sur 6 mois |
| **🌙 Luminosité Nocturne** | 3 | VIIRS DNB | Activité humaine nocturne |

**Total : 24 points**

### **Nouvelles Classifications**
- **🟢 ACTIVE** : >12 points (56.7% → ~60% attendu)
- **🟠 SEMI-ACTIVE** : 8-12 points (41.8% → ~35% attendu)
- **🔴 INACTIVE** : <8 points (1.4% → ~5% attendu)

## 🚀 Workflow MVP

### **Phase 1 : Préparation (1-2 jours)**

#### **1.1 Sélection des 200 Fincas d'Entraînement**
```bash
python scripts/select_roof_training_fincas.py
```

**Stratégie de sélection :**
- **40% actives** (80 fincas) - État toiture probablement bon
- **40% semi-actives** (80 fincas) - État toiture variable
- **20% inactives** (40 fincas) - État toiture probablement mauvais

**Critères de diversité :**
- Différentes zones géographiques d'Ibiza
- Types de toitures variés (tuiles, béton, métal)
- Tailles de fincas différentes
- Réutilisation des images véhicules existantes

#### **1.2 Réutilisation des Images Véhicules**
```bash
python scripts/reuse_vehicle_images_for_roofs.py
```

**Paramètres identiques :**
- **Zoom Mapbox** : 19 (même que véhicules)
- **Format** : 1280x960 pixels
- **Crop** : 960x720 pixels (zone centrale)
- **Cache** : Réutilisation des images existantes

### **Phase 2 : Annotation Roboflow (2-3 jours)**

#### **2.1 Création du Projet**
- **Projet** : `fincalert/roof-condition-detection`
- **Classes** : 3 (roof_good, roof_medium, roof_bad)
- **Format** : YOLO v8

#### **2.2 Guidelines d'Annotation**

**🏠 roof_good (Classe 0)**
- Toiture intacte et en bon état
- Couleurs vives et uniformes
- Pas de dégradation visible
- Tuiles bien alignées
- Pas de végétation sur le toit

**🏠 roof_medium (Classe 1)**
- Légères dégradations visibles
- Couleurs ternies mais pas dégradées
- Quelques tuiles manquantes ou déplacées
- Légère végétation ou mousse
- État général acceptable

**🏠 roof_bad (Classe 2)**
- Dégradations importantes
- Holes ou effondrements visibles
- Végétation importante sur le toit
- Couleurs très dégradées
- État général mauvais

### **Phase 3 : Entraînement (1 jour)**

#### **3.1 Configuration d'Entraînement**
```bash
python scripts/train_roof_detection_model.py
```

**Paramètres optimaux :**
- **Modèle** : YOLOv8s (équilibré performance/précision)
- **Époques** : 75
- **Batch size** : 16
- **Image size** : 640x640
- **Confidence threshold** : 0.4

**Métriques cibles :**
- **mAP@50** : >75%
- **Precision** : >80%
- **Recall** : >85%

### **Phase 4 : Test (1 jour)**

#### **4.1 Test sur 400 Fincas**
```bash
python scripts/test_roof_detection_400_fincas.py
```

**Validation :**
- Images avec boîtes de détection
- Statistiques de distribution
- Corrélation avec scores d'abandon existants
- Visualisations des résultats

## 📁 Structure des Fichiers

### **Dataset d'Entraînement**
```
data/roof_training_dataset/
├── roof_training_metadata.json      # Métadonnées des 200 fincas
├── roof_annotation_list.json        # Liste pour annotation
├── roof_training_fincas.csv         # CSV pour Roboflow
├── images/                          # Images des 200 fincas
├── roboflow_ready/                  # Structure YOLO
│   ├── data.yaml                    # Configuration YOLO
│   ├── train/images/                # 140 images (70%)
│   ├── train/labels/                # Annotations train
│   ├── valid/images/                # 40 images (20%)
│   ├── valid/labels/                # Annotations validation
│   ├── test/images/                 # 20 images (10%)
│   └── test/labels/                 # Annotations test
├── annotation_guide.md              # Guide d'annotation
└── upload_to_roboflow.py           # Script d'upload
```

### **Résultats d'Entraînement**
```
runs/roof_detection/
├── train/                           # Résultats d'entraînement
│   ├── weights/best.pt             # Meilleur modèle
│   ├── weights/last.pt             # Dernier modèle
│   └── results.png                 # Graphiques de performance
└── val/                            # Résultats de validation
```

### **Test sur 400 Fincas**
```
data/roof_test_results/
├── roof_test_report.json           # Rapport principal
├── roof_test_results.json          # Résultats détaillés
├── roof_test_summary.csv           # Résumé CSV
└── visualizations/                 # Images avec détections
    ├── finca_00001_detection.jpg
    ├── finca_00002_detection.jpg
    └── ...
```

## 🔧 Scripts Développés

### **1. Sélection des Fincas**
```python
# scripts/select_roof_training_fincas.py
- Chargement des données GeoJSON
- Sélection stratifiée (40/40/20)
- Création des métadonnées
- Export CSV pour Roboflow
```

### **2. Réutilisation des Images**
```python
# scripts/reuse_vehicle_images_for_roofs.py
- Vérification des images existantes
- Téléchargement des images manquantes
- Création structure Roboflow
- Guide d'annotation
- Script d'upload
```

### **3. Entraînement du Modèle**
```python
# scripts/train_roof_detection_model.py
- Vérification du dataset
- Configuration environnement
- Entraînement YOLOv8
- Évaluation du modèle
- Création module détection
- Rapport d'entraînement
```

### **4. Test sur 400 Fincas**
```python
# scripts/test_roof_detection_400_fincas.py
- Sélection des fincas de test
- Téléchargement des images
- Détection avec le modèle
- Création visualisations
- Analyse des résultats
- Rapport de test
```

## 📈 Métriques Attendues

### **Performance du Modèle**
- **mAP@50** : 75-85%
- **Precision** : 80-90%
- **Recall** : 85-95%
- **Temps d'inférence** : <1 seconde par image

### **Distribution des États**
- **roof_good** : ~40% (fincas actives)
- **roof_medium** : ~40% (fincas semi-actives)
- **roof_bad** : ~20% (fincas inactives)

### **Corrélation avec Score d'Abandon**
- **Corrélation attendue** : 0.3-0.5
- **Amélioration scoring** : +10-15% de précision

## 🎯 Intégration Future

### **Phase 5 : Intégration Système (1 jour)**

#### **5.1 Mise à Jour du Scoring**
```python
# Nouveau système 24 points
total_score_24 = (
    car_score +           # 5 points
    roof_score +          # 4 points (NOUVEAU)
    creation_score +      # 5 points
    vegetation_score +    # 4 points
    radar_score +         # 3 points
    luminosity_score      # 3 points
)
```

#### **5.2 Interface Utilisateur**
```typescript
// Nouveau critère dans le popup
interface FincaPopup {
  // ... propriétés existantes
  roof_condition: {
    condition: 'roof_good' | 'roof_medium' | 'roof_bad';
    score: number;
    level: string;
  };
}
```

#### **5.3 API Backend**
```python
# Nouvel endpoint
@app.get("/api/roof-condition/{finca_id}")
async def get_roof_condition(finca_id: str):
    # Détection en temps réel ou depuis cache
    return {
        "roof_condition": "roof_good",
        "score": 4,
        "level": "Bon état",
        "confidence": 0.85
    }
```

## ⏱️ Planning Estimé

| Phase | Durée | Responsabilité |
|-------|-------|----------------|
| **1. Préparation** | 1-2 jours | Développeur |
| **2. Annotation** | 2-3 jours | Utilisateur |
| **3. Entraînement** | 1 jour | Développeur |
| **4. Test** | 1 jour | Développeur |
| **5. Intégration** | 1 jour | Développeur |

**Total : 6-8 jours**

## 🚀 Commandes d'Exécution

### **Workflow Complet**
```bash
# 1. Sélection des fincas
python scripts/select_roof_training_fincas.py

# 2. Préparation des images
python scripts/reuse_vehicle_images_for_roofs.py

# 3. Upload vers Roboflow (après annotation)
cd data/roof_training_dataset
python upload_to_roboflow.py

# 4. Entraînement (après annotation)
python scripts/train_roof_detection_model.py

# 5. Test sur 400 fincas
python scripts/test_roof_detection_400_fincas.py
```

## 📊 Validation et Qualité

### **Critères de Succès**
- **Performance modèle** : mAP@50 > 75%
- **Distribution réaliste** : 40/40/20 des états
- **Corrélation positive** : > 0.3 avec score d'abandon
- **Temps d'inférence** : < 1 seconde par image

### **Validation Humaine**
- **Échantillon aléatoire** : 50 fincas testées manuellement
- **Précision humaine** : > 90% sur échantillon
- **Cohérence annotations** : Même annotateur pour cohérence

## 🔄 Prochaines Étapes

### **Après MVP Réussi**
1. **Intégration complète** dans le système de scoring
2. **Mise à jour interface** utilisateur
3. **Monitoring continu** des performances
4. **Optimisation modèle** si nécessaire
5. **Extension** à d'autres critères visuels

### **Améliorations Futures**
- **Détection piscines** : État et entretien
- **Détection végétation** : Sur les toitures
- **Analyse temporelle** : Évolution de l'état
- **Détection anomalies** : Effondrements, incendies

---

**Date de création :** 27 août 2025  
**Version :** MVP 1.0  
**Statut :** Planification complète  
**Prochaine étape :** Exécution Phase 1

