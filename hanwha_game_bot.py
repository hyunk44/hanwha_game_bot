import requests
import json
import os
import argparse
from datetime import datetime

# 슬랙 웹훅 URL
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOKURL"

# 스크립트 파일의 디렉토리
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 네이버 스포츠 API URL
API_URL = 'https://api-gw.sports.naver.com/schedule/today-games'

def fetch_game_info(today_date):
    params = {
        'fields': 'basic,superCategoryId,categoryName,upperCategoryId,upperCategoryName,stadium,statusNum,gameOnAir,hasVideo,title,specialMatchInfo,roundCode,seriesOutcome,seriesGameNo,homeStarterName,awayStarterName,winPitcherName,losePitcherName,homeCurrentPitcherName,awayCurrentPitcherName,broadChannel,matchRound,roundTournamentInfo,phaseCode,groupName,leg,hasPtSore,homePtScore,awayPtScore,league,leagueName,aggregateWinner,neutralGround,postponed,conference,round,groupName,round,generalInfo3',
        'date': today_date
    }
    response = requests.get(API_URL, params=params)
    games = response.json().get('result', {}).get('games', [])

    # 한화 이글스 경기 정보 추출
    for game in games:
        if game['categoryId'] == 'kbo' and ('한화' in game['homeTeamName'] or '한화' in game['awayTeamName']):
        # if game['gameId'] == '2024052263050187675':
            return {
                'date': game['gameDate'],
                'game_date_time': game['gameDateTime'],
                'home_team': game['homeTeamName'],
                'away_team': game['awayTeamName'],
                'home_score': game.get('homeTeamScore', '0'),
                'away_score': game.get('awayTeamScore', '0'),
                'status_info': game['statusInfo'],
                'status_code': game['statusCode'],
                'cancel': game['cancel']
            }
    return None

def send_slack_message(message):
    payload = {'text': message}
    requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'})

def print_console(message):
    print(message)

def get_previous_score(date):
    file_path = os.path.join(BASE_DIR, f'previous_score_{date}.txt')
    if not os.path.exists(file_path):
        return None

    with open(file_path, 'r') as file:
        return file.read().strip()

def set_previous_score(date, score):
    file_path = os.path.join(BASE_DIR, f'previous_score_{date}.txt')
    with open(file_path, 'w') as file:
        file.write(score)

def get_game_status(date):
    file_path = os.path.join(BASE_DIR, f'game_status_{date}.txt')
    if not os.path.exists(file_path):
        return None

    with open(file_path, 'r') as file:
        return file.read().strip()

def set_game_status(date, status):
    file_path = os.path.join(BASE_DIR, f'game_status_{date}.txt')
    with open(file_path, 'w') as file:
        file.write(status)

def get_game_date_time(date):
    file_path = os.path.join(BASE_DIR, f'game_date_time_{date}.txt')
    if not os.path.exists(file_path):
        return None

    with open(file_path, 'r') as file:
        return file.read().strip()

def set_game_date_time(date, date_time):
    file_path = os.path.join(BASE_DIR, f'game_date_time_{date}.txt')
    with open(file_path, 'w') as file:
        file.write(date_time)

def check_game_update(notify_method):
    current_time = datetime.now()
    today_date = current_time.strftime('%Y-%m-%d')

    # 결과난 이후 불필요한 API호출 방지
    game_status = get_game_status(today_date)
    if game_status and game_status == 'RESULT':
        return

    # 시작시간 이전에 불필요한 API호출 방지
    game_date_time = get_game_date_time(today_date)
    if game_date_time and current_time < datetime.fromisoformat(game_date_time):
        return

    game_info = fetch_game_info(today_date)
    
    if game_info:
        previous_score = get_previous_score(today_date)
        current_date = game_info['date']
        current_score = f"{game_info['home_score']}:{game_info['away_score']}"
        cancel = game_info['cancel']

        if not game_date_time:
            set_game_date_time(today_date, game_info['game_date_time'])

        # BEFORE, READY, STARTED, RESULT
        status_code = game_info['status_code']
        status_info = game_info['status_info']

        if cancel:
            message = f"경기 취소: {game_info['home_team']} vs {game_info['away_team']}"
            notify_method(message)
            set_game_status(current_date, 'RESULT')

        elif status_code == 'STARTED' and not game_status:
            message = f"경기 시작: {game_info['home_team']} vs {game_info['away_team']}\n점수: {current_score}"
            notify_method(message)
            set_game_status(current_date, status_code)
            set_previous_score(current_date, current_score)
        
        elif status_code == 'STARTED' and game_status == 'STARTED':
            if current_score != previous_score:
                message = f"점수 변동: {game_info['home_team']} vs {game_info['away_team']}\n{status_info}\n점수: {current_score}"
                notify_method(message)
                set_previous_score(current_date, current_score)
        
        elif status_code == 'RESULT' and game_status == 'STARTED':
            message = f"경기 종료: {game_info['home_team']} vs {game_info['away_team']}\n최종 점수: {current_score}"
            notify_method(message)
            set_game_status(current_date, status_code)
            set_previous_score(current_date, current_score)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Hanwha Eagles Game Notifier')
    parser.add_argument('--notify', choices=['slack', 'console'], default='console', help='Notification method: slack or console')
    args = parser.parse_args()

    if args.notify == 'slack':
        notify_method = send_slack_message
    else:
        notify_method = print_console

    check_game_update(notify_method)
