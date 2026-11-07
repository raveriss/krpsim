# Sources du guide « Comprendre krpsim_verif »

Ce dossier contient la source éditable du PDF et ses preuves de vérification.
Le programme et l'ancien PDF sont conservés. Exécuter les commandes depuis
la racine du dépôt krpsim, avec ce dossier dans `output/pdf/eli5_source/`.

## Régénérer le PDF

```bash
uv run --no-project --python 3.10 --with weasyprint==70.0 python output/pdf/eli5_source/build.py
```

Le moteur WeasyPrint utilise les bibliothèques système Pango/Fontconfig.
Il conserve les textes sélectionnables, les liens internes et la police Inter
intégrée. Les fontes Inter 3.19 et leur licence sont fournies dans `fonts/`.
Le chiffre arabe de l'exemple E24 utilise la fonte système Noto Sans Arabic
comme repli ; elle est également incorporée dans le PDF livré. Pour régénérer
ce caractère à l'identique, rendre cette fonte disponible via Fontconfig.

Sorties : `../krpsim_verif_arbre_de_decision_eli5.pdf`, `guide.html` et
`matrice_tracabilite.csv`. Ouvrir le HTML permet aussi de consulter la source
visuelle ; le PDF est la version paginée de référence.

## Modifier le contenu

- `content.json` : toutes les questions, explications, branches et pages.
- `style.css` : couleurs, espacements, tailles et géométrie des logigrammes.
- `build.py` : assemblage HTML, export PDF et matrice CSV.
- `matrice_tracabilite.csv` : une ligne par décision, avec condition exacte,
  fonction, références, conséquences, explication, exemple et preuve associée.

Les références de ligne correspondent aux fichiers recensés dans
`source_manifest.json`. Après une modification du programme, les relire avant
de régénérer le document ; le générateur ne réanalyse pas automatiquement le code.

## Rejouer les exemples et contrôler le PDF

```bash
PYTHONPATH=src uv run --no-project --python 3.10 python output/pdf/eli5_source/verify_examples.py
uv run --no-project --python 3.10 --with pymupdf==1.28.2 python output/pdf/eli5_source/audit_pdf.py
```

`verify_examples.py` recrée les fichiers du sous-dossier `examples/`, vérifie
30 cas et enregistre les observations dans `example_results.json`.
Les erreurs attendues font partie des exemples : un refus correct est une réussite
de l'exemple. API01 est un appel Python direct ; EX02 est le deuxième exercice.

`audit_pdf.py` vérifie les pages, les identifiants, les renvois, les limites de page
et les fontes incorporées. Il ne remplace pas le contrôle visuel.

```bash
mkdir -p tmp/pdfs/eli5
pdftoppm -scale-to 1300 -png output/pdf/krpsim_verif_arbre_de_decision_eli5.pdf tmp/pdfs/eli5/page
```

Inspecter les images après toute modification de contenu ou de mise en page.
Le bilan des vérifications effectuées et les limites CI figurent dans `validation.md`.
