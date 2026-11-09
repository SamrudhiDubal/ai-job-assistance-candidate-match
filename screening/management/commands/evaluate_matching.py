from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compare the ranking quality of the rule-based, ML and DL screening signals"

    def add_arguments(self, parser):
        parser.add_argument("--per-role", type=int, default=25, help="Resumes per category in the test pool")

    def handle(self, *args, per_role, **opts):
        from screening.ml.evaluate import RESULTS_PATH, evaluate

        r = evaluate(per_role=per_role, log=self.stdout.write)
        self.stdout.write(f"\n{r['pool_size']} resumes x {r['jobs']} jobs, semantic backend: {r['semantic_backend']}\n")
        self.stdout.write(f"{'Method':28} {'P@10':>6} {'MAP':>6} {'NDCG@10':>8}")
        for name, m in r["methods"].items():
            self.stdout.write(f"{name:28} {m['precision_at_10']:>6.3f} {m['map']:>6.3f} {m['ndcg_at_10']:>8.3f}")
        self.stdout.write(self.style.SUCCESS(f"Saved to {RESULTS_PATH}"))
