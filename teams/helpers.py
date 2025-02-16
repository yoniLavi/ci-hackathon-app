from copy import deepcopy
from datetime import datetime
import math

import pytz

from .lists import LMS_LEVELS
from accounts.models import CustomUser
from hackathon.models import Hackathon, HackTeam


def choose_team_sizes(participants, teamsize):
    """ Calculates the number of teams and teamsizes needed based on the amount
    of participants and a given wanted team size

    If the remainder when comparing participants to the wanted teamsize is 0,
    all teams will be the wanted team size.

    If the the remainder is more than half of the wanted team size,
    the remainder will be the size of the last team.

    If the the remainder is less than half of the wanted team size,
    the the remainder will be distributed to one or more teams.

    Returns a list where the number of elements is represents the amount of
    teams and the value of each element represents the number of team members
    within that team """
    remainder = len(participants) % teamsize
    num_teams = int(len(participants) / teamsize)
    if remainder > 0:
        split_to_teams = remainder < (teamsize / 2)
        if not split_to_teams:
            return [teamsize for team in range(num_teams)] + [remainder]
        else:
            teams = []
            for team in range(num_teams):
                if remainder > 0:
                    teams.append(teamsize + 1)
                    remainder -= 1
                    continue
                teams.append(teamsize)
            return teams
    return [teamsize for team in range(num_teams)]


def choose_team_levels(num_teams, hackathon_level):
    """ Calculates the average experience level per team and distributes any
    remaining difference among some of the teams evenly

    Returns a list of team_levels """
    avg_team_level = math.floor(hackathon_level / num_teams)
    team_levels = []
    remainder = hackathon_level % num_teams
    remainder_per_team = math.ceil(remainder / num_teams)
    if remainder > 0:
        while remainder > 0:
            team_levels.append(avg_team_level + remainder_per_team)
            remainder -= remainder_per_team
    num_team_with_avg_level = num_teams - len(team_levels)
    teams_at_normal_level = [avg_team_level for team
                             in range(num_team_with_avg_level)]
    return team_levels + teams_at_normal_level


def group_participants(participants, num_teams):
    """ Groups participants based on their experience level based on where
    they are in the programme

    Returns a dict with the experience level as key and the grouped student
    list as value and also returns the sum of all of the participants'
    experience level """
    participant_groups = {}
    hackathon_level = 0
    for participant in participants:
        participant_level = (LMS_LEVELS.get(participant.current_lms_module)
                             or 1)
        hackathon_level += participant_level
        participant_groups.setdefault(participant_level, [])
        participant_groups[participant_level].append(
            participant.to_team_member())
    return participant_groups, hackathon_level


def find_group_combinations(participant_levels, team_size, team_level,
                            missing):
    """ Finds all possible combinations based on the list of participants'
    experience levels, the team size and the team's wanted combined
    experience level

    Returns a list of combinations as a list """
    numbers = [i for i in range(10)]
    minimum = int(team_size * str(min(participant_levels)))
    maximum = int(team_size * str(max(participant_levels)))

    combos = []
    for i in range(minimum, maximum + 1):
        combo = sorted(list(str(i)))
        combos.append(combo)

    fitting_combos = []
    numbers_to_exclude = list(set(numbers) - set(participant_levels))
    for combo in combos:
        c = [int(num) for num in list(combo)]
        if any(num in c for num in numbers_to_exclude):
            continue
        elif team_level-missing < sum(c) < team_level + missing:
            fitting_combos.append(c)

    return fitting_combos


def find_all_combinations(participants, team_sizes):
    """ Finds all possible experience level combinations for specific team
    sizes with duplicated experience levels (e.g. (1, 1, 2))

    Returns a list of tuples representing all the possible combinations """
    num_teams = len(team_sizes)
    participant_levels = [LMS_LEVELS.get(participant.current_lms_module) or 1
                          for participant in participants]
    hackathon_level = sum(participant_levels)
    team_level = math.floor(hackathon_level / num_teams)
    missing = hackathon_level - (num_teams * team_level)
    team_sizes = list(set(team_sizes))
    combos = []
    for team_size in team_sizes:
        combos += find_group_combinations(participant_levels, team_size,
                                          team_level, missing)
    # to remove differently sorted combinations with the same elements
    sorted_combinations = [sorted(combo) for combo in combos]
    combos_without_dupes = list(set(set(tuple(i)
                                    for i in sorted_combinations)))
    return combos_without_dupes


def distribute_participants_to_teams(team_sizes, team_levels,
                                     participants, combos):
    """ Selects participants based on their skill level and distributes them
    to a team based on the wanted team size and combined experience level per
    team

    Returns a dict with the teams and any participants who could not be
    distributed to a team to be distributed manually """
    teams = {}
    team_num = 1
    team_size = team_sizes.pop(0)
    team_level = team_levels.pop(0)

    while team_size:
        combos_to_pick_from = [c for c in combos
                               if sum(c) == team_level
                               and len(c) == team_size]
        for combo in combos_to_pick_from:
            # Try to pick the participants from a copy of the participants
            # if there are not enough participants for the combo skip
            # otherwise pick them from the actual participants dict
            participants_copy = deepcopy(participants)
            try:
                members = [participants_copy[c].pop() for c in combo]
            except IndexError:
                continue

            members = [participants[c].pop() for c in combo]
            teams[f'team_{team_num}'] = members
            team_num += 1

        if not team_sizes:
            break
        team_size = team_sizes.pop(0)
        team_level = team_levels.pop(0)

    return teams, participants


def create_new_team_and_add_participants(created_by_user, team_name,
                                         team_members, hackathon):
    """ Creates a new team and assigns the team members as participants """
    hack_team = HackTeam(
        created_by=created_by_user,
        display_name=team_name,
        hackathon=hackathon
    )
    hack_team.save()
    hack_team.participants.set(get_users_from_ids(team_members))
    return hack_team


def get_users_from_ids(team_members):
    """ Retrieves the list of custom users based on their user ids """
    user_ids = [user.get('userid') for user in team_members
                if user is not None]
    return CustomUser.objects.filter(id__in=user_ids)


def create_teams_in_view(request_user, teams, hackathon_id):
    """ Creates a new HackTeam for each team and assigns the team members as
    participants """
    for team_name, team_members in teams.items():
        if len(team_members) == 0:
            continue

        create_new_team_and_add_participants(
            created_by_user=request_user,
            team_name=team_name,
            team_members=team_members,
            hackathon=Hackathon.objects.get(id=hackathon_id)
        )


def update_team_participants(created_by_user, teams, hackathon_id):
    """ Finds each existing HackTeam for each team and assigns the team
    members as participants """
    for team_name, team_members in teams.items():
        if len(team_members) == 0:
            continue
        hack_team = HackTeam.objects.filter(
            display_name=team_name,
            hackathon=Hackathon.objects.get(id=hackathon_id)
        )
        if hack_team:
            hack_team.first().participants.set(
                get_users_from_ids(team_members))
        else:
            hackathon = Hackathon.objects.get(id=hackathon_id)
            create_new_team_and_add_participants(created_by_user, team_name,
                                                 team_members, hackathon)


def calculate_timezone_offset(timezone, timezone_offset):
    """ Calculates the timezone offset between a timezone and a known
    timezone offset """
    tz = pytz.timezone(timezone)
    offset = (datetime.now(tz).utcoffset().total_seconds()/60/60)
    return offset - timezone_offset
