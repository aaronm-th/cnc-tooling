from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils.dateparse import parse_date

import attendance.models as amdl
from .serializers import CalendarEventSerializer

import holidays 
from datetime import timedelta

class UserCalendarFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = request.user
        start_date = parse_date(request.query_params.get('start'))
        end_date = parse_date(request.query_params.get('end'))
        
        if not start_date or not end_date:
            return Response({"error": "Zeitraum fehlt"}, status=status.HTTP_400_BAD_REQUEST)

        de_holidays = holidays.Germany(
            prov='BW', 
            years=[start_date.year, end_date.year], 
            language='de'
        )

        events = []
        processed_dates = set()

        # --- 1. SCHRITT: Feiertage markieren ---
        curr = start_date
        while curr <= end_date:
            if curr in de_holidays:
                holiday_name = de_holidays.get(curr)
                events.append(CalendarEventSerializer.from_holiday(holiday_name, curr))
                processed_dates.add(curr.isoformat())
            curr += timedelta(days=1)

        # --- 2. SCHRITT: Vorhandene WorkDays ---
        work_days = amdl.WorkDay.objects.filter(
            employee=employee, 
            date__range=[start_date, end_date]
        ).exclude(day_type=amdl.WorkDay.DayType.HOLIDAY).prefetch_related('sessions')

        for wd in work_days:
            if wd.date.isoformat() in processed_dates:
                continue

            # 2. Check: Normales freies Wochenende überspringen
            if wd.day_type == amdl.WorkDay.DayType.WEEKEND and wd.total_hours == 0:
                continue
                
            events.append(CalendarEventSerializer.from_workday(wd))
            processed_dates.add(wd.date.isoformat())

        # --- 3. SCHRITT: Urlaubsanträge ---
        leave_requests = amdl.LeaveRequest.objects.filter(
            employee=employee, 
            status__in=['pending'],
            leave_start__lte=end_date, 
            leave_end__gte=start_date
        )

        for lr in leave_requests:
            curr = lr.leave_start
            while curr <= lr.leave_end:
                iso_date = curr.isoformat()
                # ÄNDERUNG: 'and iso_date not in processed_dates' entfernt,
                # damit der offene Antrag AUCH dann erscheint, wenn bereits ein WorkDay existiert.
                if start_date <= curr <= end_date:
                    # Wochenende checken
                    if curr.weekday() < 5:
                        events.append(CalendarEventSerializer.from_leave_request(lr, curr))
                    # Hinweis: processed_dates.add(iso_date) hier optional weglassen, 
                    # falls es danach keine Schritte mehr gibt, die davon abhängen.
                curr += timedelta(days=1)

        return Response(events)

