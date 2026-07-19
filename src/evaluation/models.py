from django.db import models


class EvalRun(models.Model):
    """One evaluation run over the gold set — versioned by model + timestamp so runs are
    reproducible/comparable. `completed` is False if the run stopped early (e.g. quota)."""

    created_at = models.DateTimeField(auto_now_add=True)
    model = models.CharField(max_length=64)
    completed = models.BooleanField(default=False)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"EvalRun #{self.id} ({self.model}, {self.created_at:%Y-%m-%d %H:%M})"


class EvalResult(models.Model):
    """One (question x technique) cell of an EvalRun. Aggregated per technique / per type
    for display. `error` is set (and scores left 0) when a technique or the judge failed."""

    run = models.ForeignKey(EvalRun, on_delete=models.CASCADE, related_name="results")
    technique = models.CharField(max_length=32)
    question = models.TextField()
    qtype = models.CharField(max_length=32)
    # retrieval metrics (0-1)
    hit_at_k = models.FloatField(default=0.0)
    recall_at_k = models.FloatField(default=0.0)
    mrr = models.FloatField(default=0.0)
    # generation metrics (1-5)
    faithfulness = models.FloatField(default=0.0)
    correctness = models.FloatField(default=0.0)
    # operational
    latency_ms = models.FloatField(default=0.0)
    est_cost_usd = models.FloatField(default=0.0)
    error = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return f"{self.technique} / {self.qtype}"
