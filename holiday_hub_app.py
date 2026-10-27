import streamlit as st
import pandas as pd
import datetime
import calendar
import json
import os
import re

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Holiday Hub Booking System",
    page_icon="🏨",
    layout="wide",
)

DB_FILE = "bookings_v3_db.json"
COLUMNS = [
    "Booking ID", "Guest", "Email", "Start Date",
    "End Date", "Phone", "Flight Info", "Notes"
]
TODAY = datetime.date.today()


# ============================================================
# DATABASE / DATA PERSISTENCE
# ============================================================
def load_bookings():
    """Load existing reservations, or create sample data on first run."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)

            df = pd.DataFrame(data)
            for column in COLUMNS:
                if column not in df.columns:
                    df[column] = ""

            if not df.empty:
                for column in ("Start Date", "End Date"):
                    df[column] = pd.to_datetime(
                        df[column], errors="coerce"
                    ).dt.date

                df["Booking ID"] = df["Booking ID"].fillna("").astype(str)
                df["Guest"] = df["Guest"].fillna("").astype(str)
                for column in ("Email", "Phone", "Flight Info", "Notes"):
                    df[column] = df[column].fillna("").astype(str)

            return df[COLUMNS]

        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            st.error(
                "The booking database could not be read. "
                "The app has not replaced it with sample data, to help "
                "protect your existing reservations. Check the JSON file "
                f"and restart the app. Details: {exc}"
            )
            return pd.DataFrame(columns=COLUMNS)

    # Sample bookings are created only if no database file exists.
    return pd.DataFrame([
        {
            "Booking ID": "BK-1001",
            "Guest": "Alice Smith",
            "Email": "alice@example.com",
            "Start Date": datetime.date(2026, 10, 5),
            "End Date": datetime.date(2026, 10, 12),
            "Phone": "+1 555-0199",
            "Flight Info": "BA173",
            "Notes": "Prefers early check-in if possible.",
        },
        {
            "Booking ID": "BK-1002",
            "Guest": "Bob Jones",
            "Email": "bob@example.com",
            "Start Date": datetime.date(2026, 10, 15),
            "End Date": datetime.date(2026, 10, 20),
            "Phone": "",
            "Flight Info": "",
            "Notes": "",
        },
    ], columns=COLUMNS)


def save_bookings(df):
    """Write reservations to JSON using ISO-formatted dates."""
    saved = df.copy()
    for column in ("Start Date", "End Date"):
        saved[column] = saved[column].apply(
            lambda value: value.isoformat()
            if isinstance(value, (datetime.date, datetime.datetime, pd.Timestamp))
            else "" if pd.isna(value) else str(value)
        )

    temporary_file = DB_FILE + ".tmp"
    saved.to_json(
        temporary_file,
        orient="records",
        indent=4,
        force_ascii=False,
    )
    os.replace(temporary_file, DB_FILE)


def next_booking_id(df):
    """Return the next unused sequential BK number."""
    numbers = []
    for booking_id in df.get("Booking ID", pd.Series(dtype=str)).astype(str):
        match = re.fullmatch(r"BK-(\d+)", booking_id.strip())
        if match:
            numbers.append(int(match.group(1)))
    return f"BK-{max(numbers, default=1000) + 1}"


def valid_email_or_blank(email):
    """Email is optional; if entered, require a basic valid format."""
    email = email.strip()
    return not email or bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email))


# ============================================================
# AVAILABILITY CHECKS
# ============================================================
def has_date_conflict(bookings, check_in, check_out, exclude_id=None):
    """Check occupied nights. Checkout day can be another guest's check-in."""
    for _, booking in bookings.iterrows():
        if exclude_id is not None and str(booking["Booking ID"]) == str(exclude_id):
            continue

        start = booking["Start Date"]
        end = booking["End Date"]
        if pd.isna(start) or pd.isna(end):
            continue

        # Reservations conflict when their occupied nights overlap.
        if check_in < end and check_out > start:
            return True, str(booking["Booking ID"]), str(booking["Guest"])

    return False, None, None


# ============================================================
# SESSION STATE
# ============================================================
if "bookings" not in st.session_state:
    st.session_state.bookings = load_bookings()

if "logs" not in st.session_state:
    st.session_state.logs = [
        "System initialised. Waiting for reservation inputs."
    ]

for column in COLUMNS:
    if column not in st.session_state.bookings.columns:
        st.session_state.bookings[column] = ""
st.session_state.bookings = st.session_state.bookings[COLUMNS]


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================
st.sidebar.title("🏨 Holiday Hub Navigation")
page = st.sidebar.radio(
    "Go to:",
    ["📊 Dashboard & Calendar", "📈 Summary & Metrics", "➕ New Booking Request"],
)
st.sidebar.markdown("---")
st.sidebar.info(
    "New bookings and amendments update the calendar and register. "
    "Email addresses are optional."
)


def jump_to_today():
    """Reset the calendar selectors to the current month and year."""
    st.session_state["calendar_year"] = TODAY.year
    st.session_state["calendar_month"] = calendar.month_name[TODAY.month]


# ============================================================
# PAGE 1: DASHBOARD AND CALENDAR
# ============================================================
if page == "📊 Dashboard & Calendar":
    st.title("📊 Property Management Dashboard")
    st.subheader("Property Availability Calendar")

    # One-click navigation back to the current month and year.
    jump_col, _ = st.columns([1, 4])
    with jump_col:
        st.button(
            "📅 Jump to today",
            on_click=jump_to_today,
            use_container_width=True,
        )

    # Month and year selectors
    pick_col1, pick_col2 = st.columns([1, 2])
    year_options = list(range(TODAY.year - 5, TODAY.year + 11))

    with pick_col1:
        selected_year = st.selectbox(
            "Year",
            options=year_options,
            index=5,
            key="calendar_year",
        )

    month_names = list(calendar.month_name)[1:]
    with pick_col2:
        selected_month_name = st.selectbox(
            "Month",
            options=month_names,
            index=TODAY.month - 1,
            key="calendar_month",
        )

    year = int(selected_year)
    month = month_names.index(selected_month_name) + 1
    st.markdown(f"#### {calendar.month_name[month]} {year}")
    st.caption("Green = available · Red = booked · Today is marked in blue")

    # Native Streamlit components are used for every calendar cell.
    # This avoids raw HTML being displayed as text by Streamlit.
    month_grid = calendar.monthcalendar(year, month)
    days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    header_cols = st.columns(7)
    for idx, day_name in enumerate(days_of_week):
        header_cols[idx].markdown(f"**{day_name}**")

    for week in month_grid:
        week_cols = st.columns(7)
        for idx, day in enumerate(week):
            if day == 0:
                week_cols[idx].empty()
                continue

            current_date = datetime.date(year, month, day)
            active_bookings = []

            for _, booking in st.session_state.bookings.iterrows():
                start = booking["Start Date"]
                end = booking["End Date"]

                # Check-in is occupied; checkout day is not an occupied night.
                if (
                    pd.notna(start)
                    and pd.notna(end)
                    and start <= current_date < end
                ):
                    guest_name = str(booking["Guest"]).strip()
                    if guest_name:
                        active_bookings.append(guest_name)

            is_today = current_date == TODAY
            is_booked = bool(active_bookings)
            status = (
                f"Booked: {', '.join(active_bookings)}"
                if is_booked
                else "Available"
            )

            with week_cols[idx]:
                with st.container(border=True):
                    if is_today:
                        st.markdown(f":blue[**{day} · TODAY**]")
                    else:
                        st.markdown(f"**{day}**")

                    if is_booked:
                        st.error(status)
                    else:
                        st.success("Available")

    # Booking register
    st.markdown("---")
    st.subheader("📋 Booking Register")
    bookings = st.session_state.bookings

    if bookings.empty:
        st.info("No reservations have been recorded.")
    else:
        sorted_bookings = bookings.sort_values("Start Date", na_position="last")
        for _, row in sorted_bookings.iterrows():
            booking_id = str(row["Booking ID"])
            guest = str(row["Guest"])

            with st.container(border=True):
                info_col, dates_col, actions_col = st.columns([1.3, 1.5, 1])

                info_col.markdown(
                    f"**{guest}**  \nBooking ID: `{booking_id}`  \n"
                    f"Email: {row['Email'] or 'Not provided'}"
                )
                info_col.markdown(
                    f"Phone: {row['Phone'] or 'Not provided'}  \n"
                    f"Flight: {row['Flight Info'] or 'Not provided'}"
                )
                dates_col.markdown(
                    f"**Stay**  \n{row['Start Date']} to {row['End Date']}  \n"
                    f"**Notes:** {row['Notes'] or 'None'}"
                )

                with actions_col:
                    if st.button("Edit booking", key=f"edit_toggle_{booking_id}", use_container_width=True):
                        edit_key = f"editing_{booking_id}"
                        st.session_state[edit_key] = not st.session_state.get(edit_key, False)

                    if st.button("Cancel booking", key=f"cancel_{booking_id}", use_container_width=True):
                        st.session_state.bookings = st.session_state.bookings[
                            st.session_state.bookings["Booking ID"].astype(str) != booking_id
                        ].reset_index(drop=True)
                        save_bookings(st.session_state.bookings)
                        st.session_state.logs.append(
                            f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] Booking {booking_id} cancelled."
                        )
                        st.toast("Booking cancelled.")
                        st.rerun()

                # Amendment form
                if st.session_state.get(f"editing_{booking_id}", False):
                    with st.form(f"edit_form_{booking_id}"):
                        st.markdown(f"**Amend reservation {booking_id}**")
                        e1, e2 = st.columns(2)

                        with e1:
                            edited_guest = st.text_input(
                                "Guest full name", value=guest, key=f"edit_guest_{booking_id}"
                            )
                            edited_email = st.text_input(
                                "Email (optional)", value=str(row["Email"] or ""), key=f"edit_email_{booking_id}"
                            )
                            edited_phone = st.text_input(
                                "Phone (optional)", value=str(row["Phone"] or ""), key=f"edit_phone_{booking_id}"
                            )

                        with e2:
                            edited_start = st.date_input(
                                "Check-in", value=row["Start Date"], key=f"edit_start_{booking_id}"
                            )
                            edited_end = st.date_input(
                                "Check-out", value=row["End Date"], key=f"edit_end_{booking_id}"
                            )
                            edited_flight = st.text_input(
                                "Flight details (optional)", value=str(row["Flight Info"] or ""), key=f"edit_flight_{booking_id}"
                            )

                        edited_notes = st.text_area(
                            "Notes / special requests", value=str(row["Notes"] or ""), key=f"edit_notes_{booking_id}"
                        )
                        save_edit = st.form_submit_button("Save amendments")

                    if save_edit:
                        if not edited_guest.strip():
                            st.error("Please enter a guest name.")
                        elif edited_start >= edited_end:
                            st.error("Check-out must be after check-in.")
                        elif not valid_email_or_blank(edited_email):
                            st.error("Enter a valid email address or leave the email field blank.")
                        else:
                            conflict, other_id, other_guest = has_date_conflict(
                                st.session_state.bookings, edited_start, edited_end, exclude_id=booking_id
                            )
                            if conflict:
                                st.error(f"Those dates overlap booking {other_id} ({other_guest}).")
                            else:
                                mask = st.session_state.bookings["Booking ID"].astype(str) == booking_id
                                st.session_state.bookings.loc[mask, [
                                    "Guest", "Email", "Phone", "Start Date", "End Date", "Flight Info", "Notes"
                                ]] = [[
                                    edited_guest.strip(), edited_email.strip(), edited_phone.strip(),
                                    edited_start, edited_end, edited_flight.strip(), edited_notes.strip()
                                ]]
                                save_bookings(st.session_state.bookings)
                                st.session_state.logs.append(
                                    f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] Booking {booking_id} amended."
                                )
                                st.session_state[f"editing_{booking_id}"] = False
                                st.toast("Booking amendments saved.")
                                st.rerun()

    # Activity log
    if st.session_state.logs:
        st.markdown("---")
        with st.expander("System activity log"):
            for log in reversed(st.session_state.logs):
                st.code(log, language="text")


# ============================================================
# PAGE 2: SUMMARY AND METRICS
# ============================================================
elif page == "📈 Summary & Metrics":
    st.title("📈 Booking Summary & Metrics")
    st.caption(
        "A quick overview of past stays, current guests, upcoming reservations "
        "and expected occupancy."
    )

    today = datetime.date.today()
    window_end = today + datetime.timedelta(days=30)  # exclusive end date

    def to_date(value):
        """Convert a stored date value to a date, returning None if invalid."""
        try:
            if value is None or pd.isna(value):
                return None
        except (TypeError, ValueError):
            return None

        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value

        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.date()

    # Build a clean list for metrics. Invalid/incomplete date ranges are ignored.
    records = []
    for _, booking in st.session_state.bookings.iterrows():
        start = to_date(booking["Start Date"])
        end = to_date(booking["End Date"])
        if start is None or end is None or start >= end:
            continue

        records.append({
            "Booking ID": str(booking["Booking ID"]),
            "Guest": str(booking["Guest"]).strip() or "Guest name not provided",
            "Check-in": start,
            "Check-out": end,
        })

    past_bookings = [booking for booking in records if booking["Check-out"] <= today]
    current_bookings = [
        booking for booking in records
        if booking["Check-in"] <= today < booking["Check-out"]
    ]
    upcoming_bookings = [booking for booking in records if booking["Check-in"] > today]
    next_30_bookings = [
        booking for booking in records
        if booking["Check-in"] < window_end and booking["Check-out"] > today
    ]

    past_bookings.sort(key=lambda booking: booking["Check-out"], reverse=True)
    current_bookings.sort(key=lambda booking: booking["Check-in"])
    upcoming_bookings.sort(key=lambda booking: booking["Check-in"])
    next_30_bookings.sort(key=lambda booking: booking["Check-in"])

    # Occupancy is calculated by occupied nights, counting each calendar night once.
    period_dates = [today + datetime.timedelta(days=offset) for offset in range(30)]
    occupied_dates = set()
    daily_occupancy = []
    for day in period_dates:
        occupied = any(
            booking["Check-in"] <= day < booking["Check-out"]
            for booking in records
        )
        if occupied:
            occupied_dates.add(day)
        daily_occupancy.append({
            # Use a real timestamp so the chart keeps dates in chronological order.
            "Date": pd.Timestamp(day),
            "Occupancy": 100 if occupied else 0,
        })

    occupied_nights = len(occupied_dates)
    occupancy_rate = occupied_nights / 30 * 100

    metric_cols = st.columns(5)
    metric_cols[0].metric("Passed bookings", len(past_bookings))
    metric_cols[1].metric("Currently staying", len(current_bookings))
    metric_cols[2].metric("Upcoming bookings", len(upcoming_bookings))
    metric_cols[3].metric("Bookings in next 30 days", len(next_30_bookings))
    metric_cols[4].metric("Occupancy · next 30 days", f"{occupancy_rate:.0f}%", f"{occupied_nights} of 30 nights")

    st.markdown("### At a glance")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("**Bookings by status**")
        status_chart = pd.DataFrame({
            "Status": ["Passed", "Currently staying", "Upcoming"],
            "Bookings": [len(past_bookings), len(current_bookings), len(upcoming_bookings)],
        })
        st.bar_chart(status_chart, x="Status", y="Bookings", height=280)

    with chart_col2:
        st.markdown("**Occupancy over the next 30 days**")
        occupancy_chart = pd.DataFrame(daily_occupancy)
        st.bar_chart(occupancy_chart, x="Date", y="Occupancy", height=280)
        st.caption(
            "Each bar represents one night: 100% means booked and 0% means available. "
            "Check-out dates are not counted as occupied nights."
        )

    st.markdown("### Guest booking lists")
    list_tabs = st.tabs(["🗓️ Next 30 days", "⏭️ Upcoming", "✅ Passed"])

    def show_booking_table(container, booking_list, empty_message, limit=None):
        with container:
            if not booking_list:
                st.info(empty_message)
                return
            shown = booking_list[:limit] if limit else booking_list
            table = pd.DataFrame(shown)[["Guest", "Check-in", "Check-out", "Booking ID"]]
            st.dataframe(table, hide_index=True, use_container_width=True)
            if limit and len(booking_list) > limit:
                st.caption(f"Showing the {limit} most recent passed bookings. The full history remains in the booking register.")

    show_booking_table(
        list_tabs[0], next_30_bookings,
        "No guests are booked to stay during the next 30 days."
    )
    show_booking_table(
        list_tabs[1], upcoming_bookings,
        "There are no future check-ins currently recorded."
    )
    show_booking_table(
        list_tabs[2], past_bookings,
        "There are no completed stays recorded yet.", limit=10
    )

    st.caption(
        "Definitions: a passed booking has checked out; a current stay includes today; "
        "an upcoming booking checks in after today. ‘Next 30 days’ includes any stay "
        "with at least one occupied night between today and the following 29 days."
    )


# ============================================================
# PAGE 3: CREATE A NEW BOOKING
# ============================================================
elif page == "➕ New Booking Request":
    st.title("➕ Create New Reservation")
    st.markdown("Enter the guest and stay details below. Email and phone are optional.")

    with st.form("booking_form", clear_on_submit=True):
        st.markdown("#### Guest and stay details")
        form_col1, form_col2 = st.columns(2)

        with form_col1:
            guest_name = st.text_input("Primary guest full name", placeholder="John Doe")
            guest_email = st.text_input("Guest email address (optional)", placeholder="john.doe@example.com")
            guest_phone = st.text_input("Phone number (optional)", placeholder="+44 7700 900000")

        with form_col2:
            check_in = st.date_input("Check-in date", value=TODAY, key="new_checkin")
            check_out = st.date_input(
                "Check-out date", value=TODAY + datetime.timedelta(days=7), key="new_checkout"
            )
            flight_info = st.text_input("Flight details / number (optional)", placeholder="BA123 or arrival time")

        guest_notes = st.text_area(
            "Reservation notes or special requests (optional)", placeholder="Add details here..."
        )
        submit_btn = st.form_submit_button("Create reservation", type="primary")

    if submit_btn:
        if not guest_name.strip():
            st.error("Please provide a guest name.")
        elif check_in >= check_out:
            st.error("Check-out must be after check-in.")
        elif not valid_email_or_blank(guest_email):
            st.error("Enter a valid email address or leave the email field blank.")
        else:
            conflict, other_id, other_guest = has_date_conflict(
                st.session_state.bookings, check_in, check_out
            )
            if conflict:
                st.error(f"Date conflict: these dates overlap booking {other_id} ({other_guest}).")
            else:
                new_id = next_booking_id(st.session_state.bookings)
                new_record = {
                    "Booking ID": new_id,
                    "Guest": guest_name.strip(),
                    "Email": guest_email.strip(),
                    "Start Date": check_in,
                    "End Date": check_out,
                    "Phone": guest_phone.strip(),
                    "Flight Info": flight_info.strip(),
                    "Notes": guest_notes.strip(),
                }
                st.session_state.bookings = pd.concat(
                    [st.session_state.bookings, pd.DataFrame([new_record])], ignore_index=True
                )[COLUMNS]
                save_bookings(st.session_state.bookings)

                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if guest_email.strip():
                    log_message = (
                        f"[{timestamp}] Simulated confirmation email recorded for "
                        f"{guest_email.strip()} (booking {new_id})."
                    )
                else:
                    log_message = (
                        f"[{timestamp}] Booking {new_id} created. No email supplied; "
                        "no confirmation email was recorded."
                    )
                st.session_state.logs.append(log_message)
                st.success(f"Reservation {new_id} created successfully.")
                if guest_email.strip():
                    st.caption(
                        "This app records a simulated email log. It does not send a real email."
                    )
