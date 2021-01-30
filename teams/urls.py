from django.urls import path

from .views import view_team, create_teams, clear_teams, create_project
from showcase.views import create_or_update_showcase

urlpatterns = [
     path("<int:team_id>/", view_team,
          name="view_team"),
     path("<int:team_id>/project/", create_project, name="create_project"),
     path("<int:team_id>/showcase/",
          create_or_update_showcase, name="create_or_update_showcase"),
     path("create/", create_teams, name="create_teams"),
     path("clear/", clear_teams, name="clear_teams"),
]
