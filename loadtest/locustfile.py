from locust import HttpUser, between, task


class SoccerIntelligenceUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task(4)
    def live_matches(self):
        self.client.get('/api/v1/matches/live')

    @task(3)
    def upcoming_matches(self):
        self.client.get('/api/v1/matches/upcoming')

    @task(2)
    def competitions(self):
        self.client.get('/api/v1/competitions')

    @task(1)
    def health(self):
        self.client.get('/health')
