"""
user_profile.py
Single dummy employee profile for the PolicyIQ demo.
This is injected into every Claude API call as context.
"""

USER_PROFILE = {
    "name":          "Sarah Mitchell",
    "band":          "Band 2",
    "title":         "Senior Consultant",
    "joining_date":  "1 October 2023",
    "tenure_years":  2.5,
    "basic_salary":  13000,
    "allowances":    3000,
    "total_salary":  16000,
    "currency":      "AED",
    "department":    "HR Consulting",
    "manager":       "James Okafor",
    "leave_year":    2026,
    "leave_entitlement": 24,
    "leave_taken":   5,
    "leave_remaining": 19,
    "leave_taken_dates": [
        "2026-01-15",
        "2026-02-10",
        "2026-02-11",
        "2026-03-20",
        "2026-04-03",
    ],
    "wfh_days_this_month": 2,
    "wfh_limit_per_month": 4,
    "probation_completed": True,
    "notice_period": "1 month",
    "health_insurance": "DHA Gold Plan",
    "air_ticket_eligible": True,
    "air_ticket_amount": 4500,
}


def get_profile_context():
    """Returns a formatted string describing the user for Claude's system prompt."""
    p = USER_PROFILE
    gratuity = round(p["tenure_years"] * 21 * (p["basic_salary"] / 30))
    return f"""
EMPLOYEE PROFILE (the person you are speaking with):
- Name: {p["name"]}
- Band: {p["band"]} — {p["title"]}
- Department: {p["department"]}
- Joining Date: {p["joining_date"]} ({p["tenure_years"]} years of service)
- Salary: AED {p["basic_salary"]:,} basic + AED {p["allowances"]:,} allowances = AED {p["total_salary"]:,} total per month
- Annual Leave {p["leave_year"]}: {p["leave_taken"]} days used, {p["leave_remaining"]} days remaining (entitlement: {p["leave_entitlement"]} days)
- Leave taken on: {", ".join(p["leave_taken_dates"])}
- WFH this month: {p["wfh_days_this_month"]} of {p["wfh_limit_per_month"]} days used
- Notice period: {p["notice_period"]}
- Probation: Completed
- Health Insurance: {p["health_insurance"]}
- Air ticket allowance: AED {p["air_ticket_amount"]:,} (eligible)
- Estimated gratuity if leaving today: AED {gratuity:,}
"""
