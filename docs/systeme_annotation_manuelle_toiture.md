# 🏠 Système d'Annotation Manuelle - État de la Toiture

## 📋 Vue d'ensemble

Le système d'annotation manuelle permet aux utilisateurs de modifier les conditions de toiture des fincas directement depuis l'interface web, avec mise à jour en temps réel des scores et classifications.

## 🎯 Objectif

- **Évaluation humaine** : Jugement visuel de l'état des toitures
- **Mise à jour temps réel** : Modification instantanée des scores
- **Traçabilité** : Historique des modifications
- **Précision** : Amélioration de la qualité des données

## 🛠️ Interface Utilisateur

### Page Roof-Scores (`/roof-scores`)

#### Fonctionnalités Principales
- **Tableau interactif** : Liste de toutes les fincas avec leurs conditions de toiture
- **Édition en ligne** : Dropdowns pour modifier les conditions
- **Prévisualisation** : Images des fincas pour jugement visuel
- **Sauvegarde automatique** : Mise à jour instantanée

#### Interface Simplifiée
- **Colonnes affichées** :
  - ID Finca
  - Image de la finca
  - État de la toiture (éditable)
  - Date de création
  - Présence voitures

- **Colonnes supprimées** :
  - Points toiture
  - Score total
  - Statut

#### Gestion d'Erreurs
- **Retry automatique** : 3 tentatives en cas d'échec réseau
- **Messages informatifs** : Feedback utilisateur détaillé
- **État de chargement** : Indicateurs visuels pendant les opérations

## 🔧 API Backend

### Endpoint Principal

```python
POST /api/update-roof-condition
```

#### Paramètres
```json
{
  "finca_id": "finca_00001",
  "roof_condition": "excellente"
}
```

#### Réponse
```json
{
  "success": true,
  "message": "Condition de toiture mise à jour avec succès",
  "updated_finca": {
    "id": "finca_00001",
    "roof_condition": "excellente",
    "total_score_25": 18,
    "total_score_classification": "Active"
  }
}
```

### Endpoint Images

```python
GET /data/roof_images/{finca_id}.jpg
```

#### Fonctionnalités
- **Recherche multi-répertoires** : Plusieurs emplacements possibles
- **Conventions de nommage** : Gestion des différents formats
- **Fallback** : Images par défaut si non trouvées

## 📊 Système de Scoring

### Critère Toiture (5 points)

| Condition | Points | Description |
|-----------|--------|-------------|
| **Excellente** | 5/5 | Toiture parfaite, aucun signe de dégradation |
| **Bonne** | 4/5 | Toiture en bon état, légères imperfections |
| **Moyenne** | 3/5 | Toiture correcte, usure normale |
| **Mauvaise** | 1/5 | Toiture dégradée, réparations nécessaires |
| **Très mauvaise** | 0/5 | Toiture très dégradée, abandon évident |

### Impact sur le Score Total

Le score de toiture s'ajoute aux 5 autres critères :
- **Présence voitures** : 5 points
- **Date création** : 5 points
- **État toiture** : 5 points ← **NOUVEAU**
- **Entretien végétation** : 5 points
- **Activité radar** : 3 points
- **Luminosité nocturne** : 2 points

**Total maximum : 25 points**

## 🔄 Workflow d'Annotation

### 1. Accès à l'Interface
- Navigation vers `/roof-scores`
- Chargement automatique des données
- Affichage du tableau avec images

### 2. Évaluation Visuelle
- **Examen de l'image** : Jugement de l'état de la toiture
- **Critères d'évaluation** :
  - Qualité des tuiles/ardoises
  - Présence de trous ou dégradations
  - État général de la structure
  - Signes d'entretien ou d'abandon

### 3. Modification
- **Sélection** : Dropdown avec les 5 conditions possibles
- **Sauvegarde automatique** : Envoi immédiat à l'API
- **Feedback** : Confirmation ou message d'erreur

### 4. Mise à Jour
- **Recalcul automatique** : Score total et classification
- **Propagation** : Mise à jour dans tous les composants
- **Cache-busting** : Rechargement des données fraîches

## 🎨 Interface Technique

### Composant React

```typescript
// RoofScoresTable.tsx
interface RoofScoresTableProps {
  fincas: Finca[];
  onConditionChange: (fincaId: string, condition: string) => Promise<void>;
}

const RoofScoresTable: React.FC<RoofScoresTableProps> = ({ fincas, onConditionChange }) => {
  // Logique d'édition et d'affichage
}
```

### Gestion d'État

```typescript
const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>({});
const [errorStates, setErrorStates] = useState<Record<string, string>>({});

const handleConditionChange = async (fincaId: string, newCondition: string) => {
  // Logique de mise à jour avec retry
};
```

## 🔒 Sécurité et Validation

### Validation Backend

```python
def validate_roof_condition(condition: str) -> bool:
    valid_conditions = ["excellente", "bonne", "moyenne", "mauvaise", "tres_mauvaise"]
    return condition in valid_conditions

def update_roof_condition(finca_id: str, condition: str):
    # Validation
    if not validate_roof_condition(condition):
        raise ValueError("Condition invalide")
    
    # Mise à jour et recalcul
    # ...
```

### Gestion d'Erreurs

#### Frontend
- **Retry automatique** : 3 tentatives en cas d'échec
- **Messages utilisateur** : Explications claires des erreurs
- **État de chargement** : Indicateurs visuels

#### Backend
- **Validation des données** : Vérification avant sauvegarde
- **Logs détaillés** : Traçabilité des modifications
- **Rollback** : Possibilité d'annuler les modifications

## 📈 Métriques et Suivi

### Statistiques d'Utilisation
- **Fincas annotées** : Nombre de modifications effectuées
- **Répartition des conditions** : Distribution des évaluations
- **Impact sur les scores** : Évolution des classifications

### Qualité des Données
- **Cohérence** : Vérification des annotations
- **Validation croisée** : Comparaison avec autres critères
- **Amélioration continue** : Ajustement des critères

## 🚀 Déploiement

### Prérequis
- **Backend** : API endpoints opérationnels
- **Frontend** : Composants React compilés
- **Données** : Images de toiture disponibles

### Configuration
```bash
# Backend
cd backend
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm start
```

### Accès
- **URL** : http://localhost:3000/roof-scores
- **API** : http://localhost:8000/api/update-roof-condition

## 🎯 Avantages du Système

### Pour les Utilisateurs
- **Interface intuitive** : Édition directe dans le tableau
- **Feedback immédiat** : Mise à jour temps réel
- **Images intégrées** : Jugement visuel facilité

### Pour le Système
- **Données de qualité** : Validation humaine
- **Flexibilité** : Modifications possibles à tout moment
- **Traçabilité** : Historique des changements

### Pour l'Analyse
- **Précision améliorée** : Critère supplémentaire
- **Répartition optimisée** : Meilleurs seuils de classification
- **Données complètes** : Couverture 100% des fincas

---

**Date de création :** 29 Août 2025  
**Version :** 1.0  
**Statut :** En production
