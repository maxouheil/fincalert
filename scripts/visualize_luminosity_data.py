#!/usr/bin/env python3
"""
🌙 Visualisation des Données de Luminosité Nocturne
Génère des graphiques et visualisations pour vérifier les données VIIRS DNB
"""

import os
import sys
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pathlib import Path
import numpy as np

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_luminosity_data():
    """Charge les données de luminosité analysées"""
    data_dir = ROOT / 'data' / 'luminosity_analysis'
    
    # Trouver le fichier de données (pas le résumé)
    json_files = [f for f in data_dir.glob('luminosity_top20_*.json') if 'summary' not in f.name]
    if not json_files:
        raise FileNotFoundError("Aucun fichier de données de luminosité trouvé")
    
    latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 Chargement des données: {latest_file}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return data


def create_luminosity_chart(finca_data, output_dir):
    """Crée un graphique de luminosité pour une finca"""
    finca_id = finca_data['finca_id']
    monthly_data = finca_data['monthly_data']
    metrics = finca_data['metrics']
    score = finca_data['score']
    reason = finca_data['reason']
    
    # Extraire les données
    dates = [datetime.strptime(item['month'], '%Y-%m') for item in monthly_data]
    luminosities = [item['luminosity'] for item in monthly_data]
    
    # Créer le graphique
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle(f'🌙 Luminosité Nocturne - {finca_id}', fontsize=16, fontweight='bold')
    
    # Graphique principal - Évolution temporelle
    ax1.plot(dates, luminosities, 'o-', linewidth=2, markersize=8, color='#FFD700')
    ax1.fill_between(dates, luminosities, alpha=0.3, color='#FFD700')
    ax1.set_ylabel('Luminosité VIIRS DNB', fontsize=12)
    ax1.set_title(f'Évolution sur 6 mois (Score: {score}/5)', fontsize=14)
    ax1.grid(True, alpha=0.3)
    
    # Ajouter la ligne de tendance
    if len(luminosities) > 1:
        z = np.polyfit(range(len(dates)), luminosities, 1)
        p = np.poly1d(z)
        ax1.plot(dates, p(range(len(dates))), "--", color='red', alpha=0.7, label=f'Tendance: {metrics["trend"]:.1f}')
        ax1.legend()
    
    # Formatage des dates
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # Graphique secondaire - Statistiques
    stats_data = {
        'Luminosité moyenne': metrics['mean_luminosity'],
        'Écart-type': metrics['std_luminosity'],
        'Min': metrics['min_luminosity'],
        'Max': metrics['max_luminosity']
    }
    
    bars = ax2.bar(stats_data.keys(), stats_data.values(), color=['#4CAF50', '#FF9800', '#2196F3', '#F44336'])
    ax2.set_ylabel('Valeur', fontsize=12)
    ax2.set_title('Statistiques de Luminosité', fontsize=14)
    ax2.grid(True, alpha=0.3)
    
    # Ajouter les valeurs sur les barres
    for bar, value in zip(bars, stats_data.values()):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{value:.2f}', ha='center', va='bottom', fontweight='bold')
    
    # Informations supplémentaires
    info_text = f"""
    📍 Coordonnées: {finca_data['coordinates']['lat']:.6f}, {finca_data['coordinates']['lon']:.6f}
    🌟 Niveau: {metrics['luminosity_level']}
    📅 Mois actifs: {metrics['active_months']}/{metrics['total_months']}
    📊 Pattern: {metrics['seasonal_pattern']}
    💡 Raison: {reason}
    """
    
    plt.figtext(0.02, 0.02, info_text, fontsize=10, bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray"))
    
    plt.tight_layout()
    
    # Sauvegarder
    output_file = output_dir / f"{finca_id}_luminosity_chart.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_file


def create_summary_chart(all_data, output_dir):
    """Crée un graphique de résumé pour toutes les fincas"""
    finca_ids = [item['finca_id'] for item in all_data if item['status'] == 'success']
    scores = [item['score'] for item in all_data if item['status'] == 'success']
    mean_luminosities = [item['metrics']['mean_luminosity'] for item in all_data if item['status'] == 'success']
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('🌙 Résumé Analyse Luminosité Nocturne - Top 20 Fincas', fontsize=18, fontweight='bold')
    
    # 1. Distribution des scores
    score_counts = {}
    for score in scores:
        score_counts[score] = score_counts.get(score, 0) + 1
    
    ax1.bar(score_counts.keys(), score_counts.values(), color=['#4CAF50', '#FF9800', '#2196F3', '#F44336', '#9C27B0'])
    ax1.set_xlabel('Score d\'Abandon', fontsize=12)
    ax1.set_ylabel('Nombre de Fincas', fontsize=12)
    ax1.set_title('Distribution des Scores', fontsize=14)
    ax1.grid(True, alpha=0.3)
    
    # 2. Luminosité vs Score
    scatter = ax2.scatter(scores, mean_luminosities, c=scores, cmap='viridis', s=100, alpha=0.7)
    ax2.set_xlabel('Score d\'Abandon', fontsize=12)
    ax2.set_ylabel('Luminosité Moyenne', fontsize=12)
    ax2.set_title('Luminosité vs Score d\'Abandon', fontsize=14)
    ax2.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax2, label='Score')
    
    # 3. Évolution temporelle moyenne
    all_months = set()
    for item in all_data:
        if item['status'] == 'success':
            for month_data in item['monthly_data']:
                all_months.add(month_data['month'])
    
    all_months = sorted(list(all_months))
    avg_luminosities = []
    
    for month in all_months:
        month_values = []
        for item in all_data:
            if item['status'] == 'success':
                for month_data in item['monthly_data']:
                    if month_data['month'] == month:
                        month_values.append(month_data['luminosity'])
        if month_values:
            avg_luminosities.append(np.mean(month_values))
        else:
            avg_luminosities.append(0)
    
    dates = [datetime.strptime(month, '%Y-%m') for month in all_months]
    ax3.plot(dates, avg_luminosities, 'o-', linewidth=3, markersize=10, color='#FFD700')
    ax3.fill_between(dates, avg_luminosities, alpha=0.3, color='#FFD700')
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_ylabel('Luminosité Moyenne', fontsize=12)
    ax3.set_title('Évolution Temporelle Moyenne', fontsize=14)
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
    
    # 4. Distribution des niveaux de luminosité
    levels = [item['metrics']['luminosity_level'] for item in all_data if item['status'] == 'success']
    level_counts = {}
    for level in levels:
        level_counts[level] = level_counts.get(level, 0) + 1
    
    colors = ['#4CAF50', '#FF9800', '#F44336']
    ax4.pie(level_counts.values(), labels=level_counts.keys(), autopct='%1.1f%%', colors=colors)
    ax4.set_title('Distribution des Niveaux de Luminosité', fontsize=14)
    
    plt.tight_layout()
    
    # Sauvegarder
    output_file = output_dir / "summary_luminosity_analysis.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_file


def create_data_table(all_data, output_dir):
    """Crée un tableau de données formaté"""
    successful_data = [item for item in all_data if item['status'] == 'success']
    
    # Créer un fichier HTML avec un tableau interactif
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🌙 Analyse Luminosité Nocturne - Top 20 Fincas</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #f2f2f2; font-weight: bold; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            .score-0 { background-color: #d4edda; }
            .score-2 { background-color: #fff3cd; }
            .score-3 { background-color: #f8d7da; }
            .score-4 { background-color: #f5c6cb; }
            .header { background-color: #343a40; color: white; padding: 20px; text-align: center; }
            .info { margin: 20px 0; padding: 15px; background-color: #e7f3ff; border-left: 4px solid #2196F3; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌙 Analyse Luminosité Nocturne - Top 20 Fincas</h1>
            <p>Données VIIRS DNB - Analyse des 12 derniers mois</p>
        </div>
        
        <div class="info">
            <h3>📊 Informations sur l'Analyse</h3>
            <p><strong>Source:</strong> VIIRS DNB (Visible Infrared Imaging Radiometer Suite Day/Night Band)</p>
            <p><strong>Période:</strong> 12 derniers mois</p>
            <p><strong>Résolution:</strong> 750m</p>
            <p><strong>Données:</strong> Luminosité nocturne moyenne par mois</p>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Finca ID</th>
                    <th>Score</th>
                    <th>Luminosité Moyenne</th>
                    <th>Niveau</th>
                    <th>Écart-type</th>
                    <th>Tendance</th>
                    <th>Mois Actifs</th>
                    <th>Pattern Saisonnier</th>
                    <th>Raison</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for item in successful_data:
        score = item['score']
        score_class = f"score-{score}"
        
        html_content += f"""
            <tr class="{score_class}">
                <td><strong>{item['finca_id']}</strong></td>
                <td><strong>{score}/5</strong></td>
                <td>{item['metrics']['mean_luminosity']:.3f}</td>
                <td>{item['metrics']['luminosity_level']}</td>
                <td>{item['metrics']['std_luminosity']:.3f}</td>
                <td>{item['metrics']['trend']:.3f}</td>
                <td>{item['metrics']['active_months']}/{item['metrics']['total_months']}</td>
                <td>{item['metrics']['seasonal_pattern']}</td>
                <td>{item['reason']}</td>
            </tr>
        """
    
    html_content += """
            </tbody>
        </table>
        
        <div class="info">
            <h3>🎯 Interprétation des Scores</h3>
            <p><strong>0/5:</strong> Activité nocturne normale (vert)</p>
            <p><strong>2/5:</strong> Diminution progressive de l'activité (jaune)</p>
            <p><strong>3/5:</strong> Luminosité modérée avec tendance (orange)</p>
            <p><strong>4/5:</strong> Luminosité modérée avec forte tendance (rouge)</p>
        </div>
    </body>
    </html>
    """
    
    output_file = output_dir / "luminosity_analysis_table.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_file


def main():
    """Fonction principale"""
    print("🌙 CRÉATION DES VISUALISATIONS")
    print("=" * 50)
    
    # Charger les données
    data = load_luminosity_data()
    
    # Créer le dossier de sortie
    output_dir = ROOT / 'data' / 'luminosity_analysis' / 'visualizations'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    successful_data = [item for item in data if item['status'] == 'success']
    print(f"📊 {len(successful_data)} fincas à visualiser")
    
    # Créer les graphiques individuels
    print("\n📈 Création des graphiques individuels...")
    for i, finca_data in enumerate(successful_data, 1):
        print(f"   [{i}/{len(successful_data)}] {finca_data['finca_id']}")
        chart_file = create_luminosity_chart(finca_data, output_dir)
        print(f"      ✅ {chart_file.name}")
    
    # Créer le graphique de résumé
    print("\n📊 Création du graphique de résumé...")
    summary_file = create_summary_chart(successful_data, output_dir)
    print(f"   ✅ {summary_file.name}")
    
    # Créer le tableau HTML
    print("\n📋 Création du tableau de données...")
    table_file = create_data_table(successful_data, output_dir)
    print(f"   ✅ {table_file.name}")
    
    print(f"\n🎉 Visualisations créées dans: {output_dir}")
    print(f"📁 {len(successful_data)} graphiques individuels")
    print(f"📊 1 graphique de résumé")
    print(f"📋 1 tableau HTML interactif")


if __name__ == "__main__":
    main()
