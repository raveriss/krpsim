"""Moteur de simulation cycle-par-cycle pour KRPSIM.

Ce module execute les processus selon la configuration et produit une trace
deterministe exploitable par la CLI et le verificateur.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

# Pour rendre le diagnostic activable sans polluer la sortie.
import logging
# Pour formaliser des contrats de donnees clairs et compacts.
from dataclasses import dataclass

# Pour limiter le couplage aux composants internes necessaires.
from .optimizer import order_processes
# Pour limiter le couplage aux composants internes necessaires.
from .parser import Config, Process


# Pour fiabiliser les objets metier via un schema declaratif.
@dataclass
# Pour encapsuler _RunningProcess autour d'un contrat clairement borne.
class _RunningProcess:
    """Etat interne d'un processus en cours d'execution.

    Attributes:
        process: Definition statique du processus lance.
        remaining: Cycles restants avant production des resultats.

    Contrat:
        ``remaining`` doit diminuer de un par cycle jusqu'a atteindre zero.
    """

    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    process: Process
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    remaining: int


# Pour encapsuler Simulator autour d'un contrat clairement borne.
class Simulator:
    """Execute les processus d'une ``Config`` sur des cycles discrets.

    Parameters:
        config: Configuration validee a simuler.

    Contrat:
        La simulation met a jour ``stocks``, ``trace`` et ``time`` de facon
        deterministe pour des entrees identiques.
    """

    # Pour isoler __init__ et faciliter son evolution sous tests.
    def __init__(self, config: Config):
        """Initialise l'etat mutable d'une execution.

        Parameters:
            config: Configuration source partagee en lecture seule.

        Returns:
            ``None``.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            L'etat initial des stocks doit partir d'une copie pour eviter les
            mutations retroactives sur la configuration d'origine.
        """
        # Pour garder un acces stable a la configuration source en lecture
        # seule.
        self.config = config
        # Pour eviter toute mutation accidentelle des donnees d'entree.
        self.stocks: dict[str, int] = config.stocks.copy()
        # Pour garantir un point de depart deterministic des cycles.
        self.time = 0
        # Pour tracer les processus differes sans melanger avec la trace finale.
        self._running: list[_RunningProcess] = []
        # Pour accumuler une trace canonique reutilisable par le verificateur.
        self.trace: list[tuple[int, str]] = []
        # Pour repartir d'un etat neutre a chaque nouvelle simulation.
        self.deadlock = False
        # Pour imposer une borne explicite avant tout lancement de processus.
        self._max_time = 0

    # Pour isoler _complete_running et faciliter son evolution sous tests.
    def _complete_running(self) -> None:
        """Termine les processus arrives a echeance sur ce cycle.

        Parameters:
            Aucun parametre.

        Returns:
            ``None``.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            Les resultats d'un processus ne doivent etre credites qu'une seule
            fois, au cycle ou ``remaining`` atteint exactement zero.
        """
        # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
        completed: list[_RunningProcess] = []
        # Pour appliquer uniformement la regle a chaque element concerne.
        for rp in self._running:
            # Pour avancer d'un cycle l'execution des processus differes.
            rp.remaining -= 1
            # Pour proteger un invariant de comparaison critique ici.
            if rp.remaining == 0:
                # Pour appliquer uniformement la regle a chaque element
                # concerne.
                for name, qty in rp.process.results.items():
                    # Pour cumuler les resultats sans supposer un stock deja
                    # present.
                    self.stocks[name] = self.stocks.get(name, 0) + qty
                # Pour deferer la suppression et eviter de muter la liste
                # iteree.
                completed.append(rp)
        # Pour appliquer uniformement la regle a chaque element concerne.
        for rp in completed:
            # Pour retirer seulement les processus reellement termines.
            self._running.remove(rp)

    # Pour isoler _start_processes et faciliter son evolution sous tests.
    def _start_processes(self) -> tuple[bool, bool]:
        """Demarre tous les processus executables au cycle courant.

        Parameters:
            Aucun parametre.

        Returns:
            Tuple ``(started, started_nonzero)`` indiquant si au moins un
            processus a demarre et si un processus non instantane est actif.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            Chaque processus demarre au plus une fois par cycle courant.
        """
        # Pour expliciter l'etat de progression de la simulation.
        started = False
        # Pour expliciter l'etat de progression de la simulation.
        started_nonzero = False
        # Pour garder un canal de diagnostic coherent dans tout le module.
        logger = logging.getLogger(__name__)
        # Pour appliquer uniformement la regle a chaque element concerne.
        for process in order_processes(self.config):
            # Pour expliciter une decision qui impacte le flux metier.
            if self.time + process.delay > self._max_time:
                # Pour ignorer ce cas et laisser la boucle traiter les suivants.
                continue
            # Pour expliciter une decision qui impacte le flux metier.
            if all(
                # Pour verifier tous les prerequis avant de consommer des
                # ressources.
                self.stocks.get(name, 0) >= qty for name, qty in process.needs.items()
            # Pour ouvrir un bloc qui porte une contrainte locale explicite.
            ):
                # Pour appliquer uniformement la regle a chaque element
                # concerne.
                for name, qty in process.needs.items():
                    # Pour consommer les besoins avant tout effet de production.
                    self.stocks[name] -= qty
                # Pour proteger un invariant de comparaison critique ici.
                if process.delay == 0:
                    # Pour appliquer uniformement la regle a chaque element
                    # concerne.
                    for name, qty in process.results.items():
                        # Pour crediter immediatement les processus sans delai.
                        self.stocks[name] = self.stocks.get(name, 0) + qty
                # Pour couvrir explicitement le cas complementaire du contrat.
                else:
                    # Pour conserver les processus differes dans un etat
                    # separe du flux instantane.
                    self._running.append(_RunningProcess(process, process.delay))
                    # Pour expliciter l'etat de progression de la simulation.
                    started_nonzero = True
                # Pour enregistrer chaque demarrage dans l'ordre canonique.
                self.trace.append((self.time, process.name))
                # Pour offrir un journal cycle/process exploitable en mode
                # verbeux.
                logger.info("%d:%s", self.time, process.name)
                # Pour expliciter l'etat de progression de la simulation.
                started = True
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return started, started_nonzero

    # Pour isoler step et faciliter son evolution sous tests.
    def step(self) -> bool:
        """Execute un cycle logique de simulation.

        Parameters:
            Aucun parametre.

        Returns:
            ``True`` si le temps doit avancer, ``False`` sinon.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            Le temps n'avance que si un travail est en cours ou demarre,
            afin d'eviter des cycles vides artificiels.
        """
        # Pour garder un etat transitoire explicite et eviter les effets caches.
        running_before = bool(self._running)
        # Pour appliquer les productions arrivees a echeance avant demarrage.
        self._complete_running()
        # Pour separer clairement demarrages instantanes et differes.
        started, started_nonzero = self._start_processes()
        # Pour expliciter l'etat de progression de la simulation.
        advance = running_before or bool(self._running) or started_nonzero
        # Pour expliciter une decision qui impacte le flux metier.
        if advance:
            # Pour avancer l'horloge uniquement quand un travail existe.
            self.time += 1
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return advance

    # Pour isoler run et faciliter son evolution sous tests.
    def run(self, max_time: int) -> list[tuple[int, str]]:
        """Lance la simulation complete jusqu'a convergence ou limite.

        Parameters:
            max_time: Dernier cycle autorise pour demarrage/avancement.

        Returns:
            Trace ordonnee des demarrages ``(cycle, process_name)``.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            ``deadlock`` vaut ``True`` seulement si aucun processus n'a pu
            demarrer alors que des processus existent.
        """
        # Pour repartir d'un etat neutre a chaque nouvelle simulation.
        self.deadlock = False
        # Pour centraliser la borne utilisee par toutes les etapes internes.
        self._max_time = max_time
        # Pour expliciter une decision qui impacte le flux metier.
        if self._custom_strategy(max_time):
            # Pour rendre a l'appelant le resultat promis par le contrat.
            return self.trace
        # Pour iterer tant que la progression fonctionnelle reste possible.
        while self.time <= max_time and self.step():
            # Pour expliciter qu'aucune action additionnelle n'est requise ici.
            pass
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if not self.trace and self.config.processes:
            # Pour marquer explicitement l'absence totale de progression
            # possible.
            self.deadlock = True
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return self.trace

    # Pour isoler _custom_strategy et faciliter son evolution sous tests.
    def _custom_strategy(self, max_time: int) -> bool:
        """Tente une optimisation fermee pour un cas topologique specifique.

        Parameters:
            max_time: Limite temporelle globale de simulation.

        Returns:
            ``True`` si la strategie a ete appliquee, sinon ``False``.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            Cette voie rapide ne s'active que si toutes les hypotheses de
            structure sont satisfaites.
        """
        # Pour n'activer la strategie custom que sur un cas strictement borne.
        target = self._single_target()
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if not target:
            # Pour rendre a l'appelant le resultat promis par le contrat.
            return False
        # Pour verifier chaque hypothese avant d'appliquer la voie optimisee.
        target_proc = self._target_process(target)
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if not target_proc:
            # Pour rendre a l'appelant le resultat promis par le contrat.
            return False
        # Pour verifier chaque hypothese avant d'appliquer la voie optimisee.
        token, main_res = self._split_resources(target_proc)
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if not (token and main_res):
            # Pour rendre a l'appelant le resultat promis par le contrat.
            return False
        # Pour verifier chaque hypothese avant d'appliquer la voie optimisee.
        booster = self._find_booster(token, main_res, target_proc)
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if not booster:  # pragma: no cover
            # Pour rendre a l'appelant le resultat promis par le contrat.
            return False
        # Pour materialiser un plan explicite avant mutation de l'etat global.
        loops, targets = self._best_loops(booster, target_proc, main_res, max_time)
        # Pour materialiser un plan explicite avant mutation de l'etat global.
        self._apply_custom_plan(booster, target_proc, loops, targets, max_time)
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return True

    # Pour isoler _single_target et faciliter son evolution sous tests.
    def _single_target(self) -> str | None:
        """Retourne la cible d'optimisation unique hors ``time``.

        Parameters:
            Aucun parametre.

        Returns:
            Nom de ressource cible ou ``None`` si le cas n'est pas admissible.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            La strategie custom ne traite qu'une seule cible metier.
        """
        # Pour deduire les preconditions de la strategie sans heuristique
        # cachee.
        targets = [t for t in (self.config.optimize or []) if t != "time"]
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return targets[0] if len(targets) == 1 else None

    # Pour isoler _target_process et faciliter son evolution sous tests.
    def _target_process(self, target: str) -> Process | None:
        """Selectionne le processus unique producteur de la cible.

        Parameters:
            target: Ressource optimisee recherchee.

        Returns:
            Processus unique producteur ou ``None`` en cas d'ambiguite.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            L'heuristique refuse les graphes avec plusieurs producteurs.
        """
        # Pour deduire les preconditions de la strategie sans heuristique
        # cachee.
        procs = [p for p in self.config.processes.values() if p.results.get(target)]
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return procs[0] if len(procs) == 1 else None

    # Pour isoler _split_resources et faciliter son evolution sous tests.
    def _split_resources(self, proc: Process) -> tuple[str | None, str | None]:
        """Separe la ressource-token et la ressource principale d'un processus.

        Parameters:
            proc: Processus cible analyse.

        Returns:
            Tuple ``(token, main_res)`` ou valeurs ``None`` si non inferable.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            Le token est une ressource auto-reproduite par le processus cible.
        """
        # Pour deduire les preconditions de la strategie sans heuristique
        # cachee.
        token = next(
            # Pour structurer la donnee sur plusieurs lignes sans ambiguite.
            (n for n, q in proc.needs.items() if proc.results.get(n, 0) >= q),
            # Pour marquer explicitement l'absence de valeur dans ce tuple.
            None,
        # Pour clore le bloc sans ambiguite de structure.
        )
        # Pour deduire les preconditions de la strategie sans heuristique
        # cachee.
        main_res = next((n for n in proc.needs if n != token), None)
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return token, main_res

    # Pour isoler _find_booster et faciliter son evolution sous tests.
    def _find_booster(
        # Pour typer explicitement les preconditions de recherche du booster.
        self, token: str, main_res: str, target_proc: Process
    # Pour ouvrir un bloc qui porte une contrainte locale explicite.
    ) -> Process | None:
        """Trouve un processus qui enrichit la ressource principale.

        Parameters:
            token: Ressource cyclique necessaire au mecanisme.
            main_res: Ressource limitante a augmenter.
            target_proc: Processus principal optimise.

        Returns:
            Processus booster compatible ou ``None``.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            Le booster doit consommer le token tout en augmentant
            strictement ``main_res`` pour etre utile.
        """
        # Pour appliquer uniformement la regle a chaque element concerne.
        for proc in self.config.processes.values():
            # Pour expliciter une decision qui impacte le flux metier.
            if (
                # Pour eviter qu'un meme processus se reference comme booster.
                proc is not target_proc
                # Pour exiger que le booster consomme bien la ressource token.
                and proc.needs.get(token)
                # Pour eviter un booster qui detruirait la ressource token.
                and proc.results.get(token, 0) >= proc.needs[token]
                # Pour retenir seulement un booster qui enrichit la ressource
                # limitante.
                and proc.results.get(main_res, 0) > proc.needs.get(main_res, 0)
            # Pour ouvrir un bloc qui porte une contrainte locale explicite.
            ):
                # Pour rendre a l'appelant le resultat promis par le contrat.
                return proc
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return None  # pragma: no cover

    # Pour isoler _best_loops et faciliter son evolution sous tests.
    def _best_loops(
        # Pour typer les parametres du calcul de compromis loops/targets.
        self, booster: Process, target_proc: Process, main_res: str, max_time: int
    # Pour ouvrir un bloc qui porte une contrainte locale explicite.
    ) -> tuple[int, int]:
        """Calcule le meilleur compromis boucles booster / cibles produites.

        Parameters:
            booster: Processus augmentant ``main_res``.
            target_proc: Processus final optimise.
            main_res: Ressource limitante pour le processus cible.
            max_time: Limite temporelle globale.

        Returns:
            Tuple ``(best_loops, best_targets)``.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            La recherche reste bornée par ``max_time`` pour conserver un
            cout de calcul previsible.
        """
        # Pour retenir le meilleur compromis pendant l'exploration.
        best_loops = 0
        # Pour retenir le meilleur compromis pendant l'exploration.
        best_targets = 0
        # Pour figer l'etat initial avant exploration des scenarios.
        init_main = self.stocks.get(main_res, 0)
        # Pour appliquer uniformement la regle a chaque element concerne.
        for loops in range(0, max_time // booster.delay + 1):
            # Pour recalculer la marge temporelle restante apres les boucles.
            time_left = max_time - loops * booster.delay
            # Pour borner les cibles possibles par le temps restant.
            possible_targets = time_left // target_proc.delay
            # Pour projeter le stock disponible apres les boucles booster.
            main_qty = init_main + loops * (
                # Pour calculer le gain net reel apporte par une boucle booster.
                booster.results.get(main_res, 0) - booster.needs.get(main_res, 0)
            # Pour clore le bloc sans ambiguite de structure.
            )
            # Pour retenir la borne la plus contraignante de production.
            produced = min(
                # Pour combiner limites temporelle et materielle sans
                # surestimer.
                possible_targets, main_qty // target_proc.needs.get(main_res, 0)
            # Pour clore le bloc sans ambiguite de structure.
            )
            # Pour expliciter une decision qui impacte le flux metier.
            if produced > best_targets:
                # Pour retenir le meilleur compromis pendant l'exploration.
                best_targets = produced
                # Pour retenir le meilleur compromis pendant l'exploration.
                best_loops = loops
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return best_loops, best_targets

    # Pour isoler _apply_custom_plan et faciliter son evolution sous tests.
    def _apply_custom_plan(
        # Pour garder une signature multiline lisible sans perte de contexte.
        self,
        # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
        booster: Process,
        # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
        target_proc: Process,
        # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
        loops: int,
        # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
        targets: int,
        # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
        max_time: int,
    # Pour ouvrir un bloc qui porte une contrainte locale explicite.
    ) -> None:
        """Applique le plan calcule et remplace l'etat courant.

        Parameters:
            booster: Processus utilise pour enrichir la ressource limitante.
            target_proc: Processus principal optimise.
            loops: Nombre d'executions booster a lancer.
            targets: Nombre d'executions cibles a lancer.
            max_time: Limite temporelle globale.

        Returns:
            ``None``.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            L'etat final de ``stocks``, ``trace`` et ``time`` doit rester
            coherent avec une execution sequentielle equivalente.
        """
        # Pour expliciter l'etat de progression de la simulation.
        time = 0
        # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
        trace: list[tuple[int, str]] = []
        # Pour separer explicitement les etats intermediaires du traitement.
        stocks = self.stocks.copy()
        # Pour appliquer uniformement la regle a chaque element concerne.
        for _ in range(loops):
            # Pour expliciter une decision qui impacte le flux metier.
            if time + booster.delay > max_time:  # pragma: no cover
                # Pour arreter la boucle des qu'une borne de securite est
                # atteinte.
                break
            # Pour appliquer uniformement la regle a chaque element concerne.
            for name, qty in booster.needs.items():
                # Pour debiter la ressource avant toute production ulterieure.
                stocks[name] -= qty
            # Pour memoriser l'execution booster dans le plan optimisé.
            trace.append((time, booster.name))
            # Pour synchroniser l'horloge locale avec la duree booster
            # appliquee.
            time += booster.delay
            # Pour appliquer uniformement la regle a chaque element concerne.
            for name, qty in booster.results.items():
                # Pour cumuler la production sans supposer un stock preexistant.
                stocks[name] = stocks.get(name, 0) + qty
        # Pour appliquer uniformement la regle a chaque element concerne.
        for _ in range(targets):
            # Pour expliciter une decision qui impacte le flux metier.
            if time + target_proc.delay > max_time:  # pragma: no cover
                # Pour arreter la boucle des qu'une borne de securite est
                # atteinte.
                break
            # Pour appliquer uniformement la regle a chaque element concerne.
            for name, qty in target_proc.needs.items():
                # Pour debiter la ressource avant toute production ulterieure.
                stocks[name] -= qty
            # Pour memoriser l'execution cible dans le plan optimisé.
            trace.append((time, target_proc.name))
            # Pour synchroniser l'horloge locale avec la duree cible appliquee.
            time += target_proc.delay
            # Pour appliquer uniformement la regle a chaque element concerne.
            for name, qty in target_proc.results.items():
                # Pour cumuler la production sans supposer un stock preexistant.
                stocks[name] = stocks.get(name, 0) + qty
        # Pour publier la trace planifiee comme resultat officiel.
        self.trace = trace
        # Pour exposer l'etat final coherent avec la trace retenue.
        self.stocks = stocks
        # Pour aligner l'horloge finale sur le plan effectivement applique.
        self.time = time
