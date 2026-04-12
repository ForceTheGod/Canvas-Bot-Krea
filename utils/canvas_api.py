import aiohttp

async def fetch_json(url, token, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as res:
            if res.status != 200:
                print(f"Error fetching {url}: HTTP {res.status}")
                return None
            return await res.json()

async def get_canvas_data(base_url, token):
    url = f"{base_url}/api/v1/courses?enrollment_state=all&include[]=total_scores&include[]=enrollments&per_page=100"
    courses = await fetch_json(url, token)
    if not isinstance(courses, list):
        return None
    data = []
    for course in courses:
        name = course.get("name")
        enrollments = course.get("enrollments", [])
        if name and enrollments:
            score = enrollments[0].get("computed_current_score")
            if score is not None:
                data.append({"Course": name, "Grade": score})
    return data

async def get_name(base_url, token):
    url = f"{base_url}/api/v1/users/self"
    data = await fetch_json(url, token)
    if not data:
        return "Unknown User"
    return data.get("name", "Unknown User")

async def get_active_courses(base_url, token):
    url = f"{base_url}/api/v1/courses?enrollment_state=active&per_page=100"
    data = await fetch_json(url, token)
    return data if isinstance(data, list) else []

async def get_course_grades(base_url, token, course_id):
    url = f"{base_url}/api/v1/courses/{course_id}/students/submissions"
    params = {
        "per_page": 100,
        "include[]": "score_statistics"
    }
    data = await fetch_json(url, token, params=params)
    return data if isinstance(data, list) else []

async def get_assignment_groups(base_url, token, course_id):
    url = f"{base_url}/api/v1/courses/{course_id}/assignment_groups"
    data = await fetch_json(url, token, params={"per_page": 100})
    return data if isinstance(data, list) else []

async def get_assignments(base_url, token, course_id):
    url = f"{base_url}/api/v1/courses/{course_id}/assignments"
    data = await fetch_json(url, token, params={"per_page": 100})
    return data if isinstance(data, list) else []

async def get_announcements(base_url, token, course_id):
    url = f"{base_url}/api/v1/announcements"
    data = await fetch_json(url, token, params={"context_codes[]": f"course_{course_id}", "per_page": 100})
    return data if isinstance(data, list) else []

async def get_calendar_events(base_url, token, start_date, end_date, context_codes):
    url = f"{base_url}/api/v1/calendar_events"
    events_data = []

    for ev_type in ["event", "assignment"]:
        params = [
            ("start_date", start_date),
            ("end_date", end_date),
            ("per_page", "100"),
            ("type", ev_type)
        ]
        for code in context_codes:
            params.append(("context_codes[]", code))
            
        data = await fetch_json(url, token, params=params)
        if isinstance(data, list):
            events_data.extend(data)
            
    return events_data

async def get_todo_items(base_url, token):
    url = f"{base_url}/api/v1/users/self/todo"
    data = await fetch_json(url, token)
    return data if isinstance(data, list) else []

async def search_course_files(base_url, token, course_id, search_term):
    url = f"{base_url}/api/v1/courses/{course_id}/files"
    params = {
        "search_term": search_term,
        "per_page": 10
    }
    data = await fetch_json(url, token, params=params)
    return data if isinstance(data, list) else []

async def get_course_syllabus(base_url, token, course_id):
    url = f"{base_url}/api/v1/courses/{course_id}"
    params = {"include[]": "syllabus_body"}
    return await fetch_json(url, token, params=params)
