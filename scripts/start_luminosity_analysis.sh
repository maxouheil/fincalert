#!/bin/bash

# 🌙 Start Luminosity Analysis - All 631 Fincas
# Script pour lancer l'analyse de luminosité avec monitoring en parallèle

echo "🌙 LANCEMENT ANALYSE LUMINOSITÉ - TOUTES LES 631 FINCAS"
echo "=================================================="
echo "📡 Utilisation des données VIIRS DNB réelles"
echo "⏱️  Monitoring en temps réel"
echo "💾 Sauvegarde automatique tous les 50 fincas"
echo "=================================================="

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "scripts/batch_luminosity_analysis_all_631.py" ]; then
    echo "❌ Erreur: Script d'analyse non trouvé"
    echo "   Assurez-vous d'être dans le répertoire racine du projet"
    exit 1
fi

# Activer l'environnement virtuel si disponible
if [ -d "venv" ]; then
    echo "🐍 Activation de l'environnement virtuel..."
    source venv/bin/activate
fi

# Créer le dossier de sortie
mkdir -p data/luminosity_analysis

echo ""
echo "🚀 DÉMARRAGE DE L'ANALYSE..."
echo ""

# Lancer l'analyse en arrière-plan
echo "📊 Lancement de l'analyse de luminosité..."
python scripts/batch_luminosity_analysis_all_631.py > luminosity_analysis.log 2>&1 &
ANALYSIS_PID=$!

echo "📊 PID de l'analyse: $ANALYSIS_PID"
echo "📄 Logs: luminosity_analysis.log"

# Attendre un peu pour que l'analyse démarre
sleep 5

echo ""
echo "📊 DÉMARRAGE DU MONITORING..."
echo ""

# Lancer le monitoring en parallèle
echo "📊 Lancement du monitoring en temps réel..."
python scripts/monitor_luminosity_progress.py &
MONITOR_PID=$!

echo "📊 PID du monitoring: $MONITOR_PID"

echo ""
echo "🎯 ANALYSE EN COURS..."
echo "=================================================="
echo "📊 Progression visible en temps réel"
echo "⏹️  Pour arrêter: Ctrl+C"
echo "📄 Logs détaillés: luminosity_analysis.log"
echo "💾 Sauvegarde: data/luminosity_analysis/"
echo "=================================================="

# Fonction de nettoyage
cleanup() {
    echo ""
    echo "🛑 Arrêt des processus..."
    
    # Arrêter l'analyse
    if kill -0 $ANALYSIS_PID 2>/dev/null; then
        echo "📊 Arrêt de l'analyse (PID: $ANALYSIS_PID)..."
        kill $ANALYSIS_PID
    fi
    
    # Arrêter le monitoring
    if kill -0 $MONITOR_PID 2>/dev/null; then
        echo "📊 Arrêt du monitoring (PID: $MONITOR_PID)..."
        kill $MONITOR_PID
    fi
    
    echo "✅ Processus arrêtés"
    echo ""
    echo "📊 RÉSUMÉ FINAL:"
    echo "   📄 Logs: luminosity_analysis.log"
    echo "   💾 Données: data/luminosity_analysis/"
    echo "   📊 Résultats: python scripts/monitor_luminosity_progress.py --final"
    echo ""
    exit 0
}

# Capturer Ctrl+C
trap cleanup SIGINT

# Attendre que l'analyse se termine
wait $ANALYSIS_PID

echo ""
echo "🎉 ANALYSE TERMINÉE!"
echo "=================================================="

# Afficher les résultats finaux
echo "📊 RÉSULTATS FINAUX:"
python scripts/monitor_luminosity_progress.py --final

echo ""
echo "📄 Logs complets: luminosity_analysis.log"
echo "💾 Données: data/luminosity_analysis/"
echo "=================================================="
