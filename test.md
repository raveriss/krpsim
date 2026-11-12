flowchart TD
    A["Lire une ligne<br/>Exemple : 20:do_armoire_ikea"] --> B["Appeler la fonction avec :<br/>current_cycle = 20<br/>les travaux déjà lancés<br/>le stock actuel"]
    B --> C["Récupérer les productions<br/>terminées au plus tard au cycle 20"]
    C --> D["Après le retour de la fonction :<br/>consommer les pièces et démarrer l’armoire"]