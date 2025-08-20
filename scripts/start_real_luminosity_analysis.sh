#!/bin/bash

# 🌙 Script de lancement - Analyse Luminosité Vraies Données VIIRS Optimisée
# Lance l'analyse avec cache et parallélisation

set -e

echo "🌙 LANCEMENT ANALYSE LUMINOSITÉ - VRAIES DONNÉES VIIRS OPTIMISÉES"
echo "=================================================================="
echo "📡 Utilisation des vraies données VIIRS DNB"
echo "⚡ Parallélisation avec cache automatique"
echo "⏱️  Monitoring en temps réel"
echo "=================================================================="

# Vérifier l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "❌ Environnement virtuel 'venv' non trouvé"
    echo "💡 Créez-le avec: python -m venv venv"
    exit 1
fi

# Activer l'environnement virtuel
echo "🔧 Activation de l'environnement virtuel..."
source venv/bin/activate

# Vérifier les dépendances
echo "📦 Vérification des dépendances..."
python -c "import ee; print('✅ Google Earth Engine OK')" 2>/dev/null || {
    echo "❌ Google Earth Engine non configuré"
    echo "💡 Configurez GEE avec: earthengine authenticate"
    exit 1
}

# Paramètres par défaut
WORKERS=${1:-3}
MONTHS=${2:-6}

echo "⚙️  Paramètres:"
echo "   🚀 Workers: $WORKERS"
echo "   📅 Mois: $MONTHS"
echo ""

# Nettoyer les anciens processus
echo "🧹 Nettoyage des anciens processus..."
pkill -f "batch_luminosity_analysis_all_631" 2>/dev/null || true
pkill -f "monitor_luminosity_progress" 2>/dev/null || true

# Créer le dossier de logs
mkdir -p logs

# Timestamp pour les logs
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/luminosity_real_analysis_${TIMESTAMP}.log"

echo "📝 Logs: $LOG_FILE"
echo ""

# Fonction de nettoyage
cleanup() {
    echo ""
    echo "🛑 Arrêt des processus..."
    pkill -f "batch_luminosity_analysis_all_631_real_optimized" 2>/dev/null || true
    echo "✅ Nettoyage terminé"
    exit 0
}

# Capturer Ctrl+C
trap cleanup SIGINT

# Lancer l'analyse en arrière-plan
echo "🚀 Lancement de l'analyse optimisée..."
echo "   📡 Vraies données VIIRS"
echo "   💾 Cache automatique"
echo "   ⚡ Parallélisation: $WORKERS workers"
echo ""

python scripts/batch_luminosity_analysis_all_631_real_optimized.py \
    --workers $WORKERS \
    --months $MONTHS \
    > "$LOG_FILE" 2>&1 &

ANALYSIS_PID=$!
echo "📊 Processus d'analyse lancé (PID: $ANALYSIS_PID)"
echo ""

# Attendre un peu pour que l'analyse démarre
sleep 3

# Vérifier que le processus fonctionne
if ! kill -0 $ANALYSIS_PID 2>/dev/null; then
    echo "❌ L'analyse s'est arrêtée prématurément"
    echo "📄 Vérifiez les logs: $LOG_FILE"
    tail -20 "$LOG_FILE"
    exit 1
fi

echo "✅ Analyse en cours..."
echo "📊 Suivi en temps réel:"
echo ""

# Suivre les logs en temps réel
tail -f "$LOG_FILE" &
TAIL_PID=$!

# Attendre la fin de l'analyse
wait $ANALYSIS_PID
ANALYSIS_EXIT_CODE=$?

# Arrêter le suivi des logs
kill $TAIL_PID 2>/dev/null || true

echo ""
echo "🏁 ANALYSE TERMINÉE"
echo "=================="

if [ $ANALYSIS_EXIT_CODE -eq 0 ]; then
    echo "✅ Analyse terminée avec succès!"
    echo ""
    echo "📊 RÉSULTATS:"
    echo "   📄 Logs complets: $LOG_FILE"
    echo "   📁 Dossier résultats: data/luminosity_analysis/"
    echo "   💾 Cache: data/luminosity_cache/"
    echo ""
    echo "📈 FICHIERS GÉNÉRÉS:"
    ls -la data/luminosity_analysis/luminosity_all631_real_*${TIMESTAMP}* 2>/dev/null || echo "   ⚠️  Aucun fichier trouvé"
else
    echo "❌ Analyse terminée avec erreur (code: $ANALYSIS_EXIT_CODE)"
    echo "📄 Vérifiez les logs: $LOG_FILE"
    echo ""
    echo "🔍 DERNIÈRES LIGNES DU LOG:"
    tail -20 "$LOG_FILE"
fi

echo ""
echo "🎉 Script de lancement terminé"
