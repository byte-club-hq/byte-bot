import requests
from dataclasses import dataclass
from typing import List
import random

@dataclass
class SubmissionStat:
    difficulty: str | None
    count: int | None

@dataclass
class Profile:
    real_name: str | None
    ranking: int | None
    reputation: int | None
    country: str | None

@dataclass
class LeetCodeUser:
    username: str | None
    profile: Profile | None
    submissions: List[SubmissionStat] | None

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
LEETCODE_PROBLEMS_URL = "https://leetcode.com/api/problems/all/"

def get_leetcode_profile(profile: str):

    # This is where the graphql query happens, we can also query for problems, found this documentation https://jacoblincool.github.io/LeetCode-Query/
    query = """
                query getUserProfile($username: String!) {
                matchedUser(username: $username) {
                    username
                    profile {
                    realName
                    ranking
                    reputation
                    countryName
                    }
                    submitStats: submitStatsGlobal {
                    acSubmissionNum {
                        difficulty
                        count
                    }
                    }
                }
                }
                """
        
    variables = {
        "username": f"{profile}"
    }
    response = requests.post(
        LEETCODE_GRAPHQL_URL,
        json={"query": query, "variables": variables}
    )

    data = response.json()

    # First check if that users profile exists
    if not (user_data := data.get("data").get("matchedUser")):
            raise ValueError("Failed to find a leetcode user with that username")
    
    # Parse the data
    profile_data = user_data.get("profile")
    submission_data = user_data.get("submitStats").get("acSubmissionNum")

    profile = Profile(
        real_name=profile_data.get("realName"),
        ranking=profile_data.get("ranking"),
        reputation=profile_data.get("reputation"),
        country=profile_data.get("countryName"),
    )

    submissions = [
        SubmissionStat(
            difficulty=stat.get("difficulty"),
            count=stat.get("count")
        )
        for stat in submission_data
    ]

    user = LeetCodeUser(
        username=user_data.get("username"),
        profile=profile,
        submissions=submissions
    )

    return user

def get_leetcode_daily():
    query = """
        query questionOfToday {
        activeDailyCodingChallengeQuestion {
            date
            link
            question {
            title
            titleSlug
            difficulty
            acRate
            questionFrontendId
            }
        }
        }
        """

    variables = {
    }
    response = requests.post(
        LEETCODE_GRAPHQL_URL,
        json={"query": query, "variables": variables}
    )

    data = response.json()

    if not (problem_data := data.get("data", {}).get("activeDailyCodingChallengeQuestion")):
        raise ValueError("Failed to find a daily leetcode problem")
    
    return problem_data

def get_leetcode_random(difficulty):
    difficulties: dict[str, int] = {"easy": 1, "medium": 2, "hard": 3}

    if difficulty is None or difficulty.lower() not in difficulties:
        raise ValueError("You must provide a difficulty: `Easy`, `Medium`, `Hard`\nUsage: `/leetcoderandom <difficulty>`\n")
    
    response = requests.get(LEETCODE_PROBLEMS_URL)
    data = response.json()
    questions = data.get("stat_status_pairs")  # list of all problems

    # Filter by difficulty
    filtered = [
        q for q in questions
        if q.get("difficulty", {}).get("level") == difficulties.get(difficulty.lower())
    ]
    
    return random.choice(filtered)
