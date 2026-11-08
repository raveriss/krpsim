
flowchart TD
    A(["DÉBUT<br/>main(argv)"])
    B["Pour savoir quels arguments<br/>le programme accepte.<br/><br/>parser = build_parser()"]

    C["Pour pouvoir tester main avec des<br/>arguments choisis, sans passer<br/>par le terminal.<br/><br/>args = parser.parse_args(argv)"]

    D["Pour savoir si les entrées permettent<br/>de poursuivre la vérification.<br/><br/>sim, exit_code = _verify_inputs(args)"]

    E{"Pour ne pas utiliser une simulation<br/>qui n'existe pas.<br/><br/>sim is not None"}

    F["Pour que l'utilisateur connaisse<br/>les quantités restantes<br/>à la fin de la simulation.<br/><br/>_print_final_stocks(sim)"]

    G(["Pour que le terminal et les tests<br/>sachent si la vérification a réussi.<br/><br/>return exit_code"])

    H(["Fin anticipée par argparse<br/>Aide demandée ou erreur d'arguments"])

    A --> B
    B --> C
    C -->|Arguments acceptés| D
    C -.->|Aide ou erreur| H
    D --> E
    E -->|Oui| F
    E -->|Non| G
    F --> G

    classDef startEnd fill:#DBEAFE,stroke:#2563EB,color:#1E3A8A
    classDef process fill:#F1F5F9,stroke:#64748B,color:#0F172A
    classDef decision fill:#FEF3C7,stroke:#D97706,color:#78350F
    classDef exception fill:#FEE2E2,stroke:#DC2626,color:#991B1B

    class A,G startEnd
    class B,C,D,F process
    class E decision
    class H exception
