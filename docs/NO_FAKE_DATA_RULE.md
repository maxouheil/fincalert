# 🚨 RÈGLE ABSOLUE : JAMAIS DE FAKE DATA

## ⚠️ **RÈGLE CRUCIALE**
**NE JAMAIS CRÉER, SIMULER OU GÉNÉRER DE FAUSSES DONNÉES**

## 📋 **Directives Strictes**

### ✅ **AUTORISÉ**
- **Données réelles** : APIs officielles, bases de données publiques
- **Données de test** : Seulement si explicitement demandé par l'utilisateur
- **Données d'exemple** : Basées sur des cas réels documentés
- **Simulation de processus** : Pour tester des workflows, PAS les données

### ❌ **INTERDIT**
- **Fake data** : Données générées aléatoirement
- **Simulation de résultats** : Données inventées pour les analyses
- **Données de démonstration** : Créées pour "faire joli"
- **Métadonnées simulées** : Informations inventées

## 🔧 **Quand l'API ne fonctionne pas**

### **Actions Correctes**
1. **Diagnostiquer le problème** : Erreurs, rate limiting, format
2. **Tester des alternatives** : Autres endpoints, formats de coordonnées
3. **Documenter l'échec** : Expliquer pourquoi les données ne sont pas disponibles
4. **Proposer des solutions** : APIs alternatives, contacts officiels
5. **Attendre les vraies données** : Ne pas "inventer" en attendant

### **Actions Interdites**
- ❌ Générer des données aléatoires
- ❌ Simuler des résultats d'analyse
- ❌ Créer des métadonnées inventées
- ❌ "Faire semblant" que ça fonctionne

## 📊 **Exemple : Cadastre Espagnol**

### ❌ **FAUX (ce que j'ai fait)**
```python
# SIMULATION INTERDITE
owner_age = random.randint(25, 85)
value = random.randint(10000, 50000)
co_ownership = random.random() < 0.2
```

### ✅ **CORRECT**
```python
# 1. Essayer l'API officielle
try:
    data = get_real_cadastre_data(lat, lon)
except Exception as e:
    # 2. Documenter l'échec
    logger.error(f"API cadastre échouée: {e}")
    # 3. Proposer des alternatives
    suggest_alternative_apis()
    # 4. Retourner None ou erreur
    return None
```

## 🎯 **Conséquences**

### **Pourquoi cette règle est cruciale**
- **Intégrité scientifique** : Les analyses doivent être basées sur des données réelles
- **Confiance** : L'utilisateur doit pouvoir faire confiance aux résultats
- **Décisions** : Les décisions business ne doivent pas être basées sur des données inventées
- **Validation** : Les modèles doivent être testés sur de vraies données

## 📝 **Checklist Avant Chaque Action**

- [ ] Les données proviennent-elles d'une source réelle ?
- [ ] Suis-je en train de "créer" quelque chose qui n'existe pas ?
- [ ] L'utilisateur sait-il que ce sont des données simulées ?
- [ ] Puis-je obtenir les vraies données d'une autre manière ?
- [ ] Est-ce que je documente clairement les limitations ?

## 🚨 **Rappel Permanent**

**TOUJOURS PRÉFÉRER :**
- ❌ Pas de données plutôt que des fake data
- ✅ Erreur claire plutôt que simulation
- ✅ Documentation des échecs plutôt que "faire semblant"
- ✅ Solutions alternatives plutôt qu'invention

---

**Cette règle est ABSOLUE et ne doit JAMAIS être violée.**
