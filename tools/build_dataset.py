"""Builds data/eval/docs/*.txt and data/eval/gold/*.json from the table below.

Run from the project root:  python tools\build_dataset.py
Flags per requirement: A = ambiguous, I = incomplete, N = non_testable.
Types: F functional, NF non_functional, BR business_rule, C constraint,
       AS assumption, D dependency, Q open_question.
Pairs are 1-based requirement numbers within a document.
"""
import json
import os

T = {"F": "functional", "NF": "non_functional", "BR": "business_rule", "C": "constraint",
     "AS": "assumption", "D": "dependency", "Q": "open_question"}
K = {"A": "ambiguous", "I": "incomplete", "N": "non_testable"}

DOCS = [
 dict(title="Library Management System", style="num", reqs=[
  ("Members must be able to search the catalogue by title, author or ISBN.", "F", ""),
  ("The system shall respond to catalogue searches within 2 seconds for 95% of requests.", "NF", ""),
  ("A member may borrow up to 5 books at a time.", "BR", ""),
  ("A member may borrow up to 8 books at a time.", "BR", ""),
  ("The system should be user friendly.", "NF", "AN"),
  ("Overdue books incur a fine.", "BR", "I"),
  ("The system depends on the university student database for member records.", "D", ""),
  ("Assumption: every book has a unique barcode.", "AS", ""),
  ("How will lost books be handled?", "Q", ""),
 ], pairs=[("conflict", 3, 4)]),
 dict(title="Hospital Appointment Booking", style="bullet", reqs=[
  ("Patients can book an appointment with a doctor online.", "F", ""),
  ("Patients can book an appointment with a doctor through the website.", "F", ""),
  ("The system must send a reminder before the appointment.", "F", "I"),
  ("Doctors can mark themselves unavailable for a date range.", "F", ""),
  ("The booking page must load quickly.", "NF", "AN"),
  ("A patient cannot hold two appointments at the same time.", "BR", ""),
  ("Patient records must be encrypted at rest and in transit.", "C", ""),
  ("Assumption: each doctor works fixed 30 minute slots.", "AS", ""),
 ], pairs=[("duplicate", 1, 2)]),
 dict(title="Ride Hailing App", style="num", reqs=[
  ("Riders must be able to request a ride from their current location.", "F", ""),
  ("The app shall show the estimated arrival time of the driver.", "F", ""),
  ("Drivers must be able to accept or decline a ride request.", "F", ""),
  ("Payment is made in cash only.", "BR", ""),
  ("Riders can pay by card or wallet inside the app.", "F", ""),
  ("The app should handle a large number of users.", "NF", "AN"),
  ("The app depends on a third party maps service for routing.", "D", ""),
  ("Fares are calculated based on distance and time.", "BR", "I"),
  ("What happens when no driver is available nearby?", "Q", ""),
 ], pairs=[("conflict", 4, 5)]),
 dict(title="HR Leave Management", style="prose", reqs=[
  ("Employees can apply for leave through the portal.", "F", ""),
  ("Managers must approve or reject a leave request within 3 working days.", "BR", ""),
  ("The system should notify the relevant people when needed.", "F", "AI"),
  ("Each employee gets 24 days of paid leave per year.", "BR", ""),
  ("Unused leave may be carried forward to the next year.", "BR", "I"),
  ("The portal must be available 99.5% of the time during working hours.", "NF", ""),
  ("The portal integrates with the existing payroll system.", "D", ""),
  ("Assumption: all employees have a company email address.", "AS", ""),
 ], pairs=[]),
 dict(title="Mobile Banking App", style="num", reqs=[
  ("Customers must log in with a password and a one time code.", "F", ""),
  ("Customers can view their last 90 days of transactions.", "F", ""),
  ("Customers can transfer money to saved beneficiaries.", "F", ""),
  ("A single transfer cannot exceed 1,00,000 rupees.", "BR", ""),
  ("A single transfer cannot exceed 5,00,000 rupees.", "BR", ""),
  ("The app must be secure.", "NF", "AN"),
  ("Transaction screens must open in under 3 seconds on a 4G connection.", "NF", ""),
  ("The app must comply with applicable banking regulations.", "C", "A"),
  ("Should the app support fingerprint login?", "Q", ""),
 ], pairs=[("conflict", 4, 5)]),
 dict(title="Food Delivery Platform", style="bullet", reqs=[
  ("Customers can browse restaurants near their location.", "F", ""),
  ("Customers can filter restaurants by cuisine and rating.", "F", ""),
  ("Customers can track their order status in real time.", "F", ""),
  ("Orders should be delivered as soon as possible.", "NF", "AN"),
  ("Restaurants must confirm an order within 5 minutes or it is cancelled automatically.", "BR", ""),
  ("Delivery partners are assigned based on proximity.", "BR", "I"),
  ("The platform depends on the payment gateway for online payments.", "D", ""),
  ("Assumption: restaurants keep their menus up to date.", "AS", ""),
  ("Customers can browse restaurants close to where they are.", "F", ""),
 ], pairs=[("duplicate", 1, 9)]),
 dict(title="E-Learning Portal", style="num", reqs=[
  ("Students can enrol in courses and view course materials.", "F", ""),
  ("Instructors can upload videos, slides and assignments.", "F", ""),
  ("Videos must be encoded so they play on low bandwidth connections.", "NF", "A"),
  ("Students must score at least 40% to pass a course.", "BR", ""),
  ("Students must score at least 50% to pass a course.", "BR", ""),
  ("The system must generate certificates for completed courses.", "F", "I"),
  ("The portal must support 2,000 concurrent students without degradation.", "NF", ""),
  ("The system relies on the college single sign on service.", "D", ""),
 ], pairs=[("conflict", 4, 5)]),
 dict(title="Hotel Booking System", style="prose", reqs=[
  ("Guests can search rooms by date, location and price range.", "F", ""),
  ("Guests can cancel a booking free of charge up to 48 hours before check in.", "BR", ""),
  ("Guests can cancel a booking free of charge up to 24 hours before check in.", "BR", ""),
  ("The system should provide a great booking experience.", "NF", "AN"),
  ("Hotel managers can update room prices and availability.", "F", ""),
  ("Confirmation emails must be sent after a successful booking.", "F", "I"),
  ("The system must be built on the company's existing cloud platform.", "C", ""),
  ("Assumption: room rates are quoted in a single currency.", "AS", ""),
 ], pairs=[("conflict", 2, 3)]),
 dict(title="Warehouse Inventory Tracker", style="num", reqs=[
  ("Staff can scan a barcode to record stock received.", "F", ""),
  ("The system must alert managers when an item falls below its reorder level.", "F", ""),
  ("Stock counts must be updated immediately when items are shipped.", "F", "A"),
  ("Only managers can adjust stock counts manually.", "BR", ""),
  ("The system should be easy to maintain.", "NF", "AN"),
  ("Reports can be exported.", "F", "I"),
  ("The scanner app must work offline and sync when connectivity returns.", "NF", ""),
  ("The tracker depends on the ERP system for product master data.", "D", ""),
  ("Who is responsible for the monthly stock audit?", "Q", ""),
 ], pairs=[]),
 dict(title="Airline Check-in", style="bullet", reqs=[
  ("Passengers can check in online between 48 hours and 2 hours before departure.", "BR", ""),
  ("Passengers can check in online from 24 hours before departure.", "BR", ""),
  ("Passengers can select a seat during check in.", "F", ""),
  ("The system shall generate a boarding pass as a PDF and as a QR code.", "F", ""),
  ("The check in process should be fast.", "NF", "AN"),
  ("Extra baggage is charged at the standard rate.", "BR", "I"),
  ("The system depends on the airline reservation system for passenger data.", "D", ""),
  ("The service must handle peak load around holidays.", "NF", "A"),
 ], pairs=[("conflict", 1, 2)]),
 dict(title="Insurance Claims Portal", style="num", reqs=[
  ("Policyholders can submit a claim with supporting documents.", "F", ""),
  ("Policyholders can upload photos and PDFs as supporting documents for a claim.", "F", ""),
  ("Claims above 50,000 rupees must be reviewed by a senior adjuster.", "BR", ""),
  ("Claims are processed efficiently.", "NF", "AN"),
  ("Adjusters can approve, reject or request more information on a claim.", "F", ""),
  ("The system must keep an audit log of every status change.", "C", ""),
  ("Policyholders are notified of decisions.", "F", "I"),
  ("Assumption: policy data is available in the policy administration system.", "AS", ""),
 ], pairs=[("duplicate", 1, 2)]),
 dict(title="Smart Home Controller", style="prose", reqs=[
  ("Users can switch lights on and off from the mobile app.", "F", ""),
  ("Users can create schedules for devices.", "F", ""),
  ("The app must respond to a command within 1 second on the home network.", "NF", ""),
  ("The hub communicates with devices over Zigbee.", "C", ""),
  ("The hub communicates with devices over Bluetooth only.", "C", ""),
  ("The system should be intuitive for all users.", "NF", "AN"),
  ("Firmware updates must be applied automatically.", "F", "I"),
  ("How many devices must one hub support?", "Q", ""),
 ], pairs=[("conflict", 4, 5)]),
 dict(title="School Attendance System", style="bullet", reqs=[
  ("Teachers can mark attendance for each class period.", "F", ""),
  ("Parents receive a message when their child is marked absent.", "F", ""),
  ("A student with attendance below 75% is not allowed to sit the final exam.", "BR", ""),
  ("Attendance data should be stored for an appropriate period.", "C", "A"),
  ("The system must be reliable.", "NF", "AN"),
  ("Teachers can correct an attendance entry within the same day.", "F", ""),
  ("Reports are generated for the principal.", "F", "I"),
  ("Assumption: every parent has registered a mobile number.", "AS", ""),
 ], pairs=[]),
 dict(title="Event Ticketing", style="num", reqs=[
  ("Customers can buy tickets for an event online.", "F", ""),
  ("A customer can buy at most 6 tickets per event.", "BR", ""),
  ("A customer can buy at most 10 tickets per event.", "BR", ""),
  ("Tickets are delivered by email as a QR code.", "F", ""),
  ("The site must stay responsive when a popular event goes on sale.", "NF", "AN"),
  ("Organisers can see sales figures.", "F", "I"),
  ("Refunds are allowed up to 7 days before the event.", "BR", ""),
  ("The system depends on the payment gateway for card payments.", "D", ""),
 ], pairs=[("conflict", 2, 3)]),
 dict(title="Payroll Processing", style="prose", reqs=[
  ("The system calculates monthly salary from base pay, allowances and deductions.", "F", ""),
  ("Payslips are generated automatically at the end of each month.", "F", ""),
  ("Payslips must be generated on the last working day of each month.", "F", ""),
  ("Salary is paid on the 1st of every month.", "BR", ""),
  ("Salary is paid on the 5th of every month.", "BR", ""),
  ("The payroll run should complete in a reasonable time.", "NF", "AN"),
  ("Tax is deducted according to the rules.", "BR", "A"),
  ("Payroll data must be accessible only to authorised HR staff.", "C", ""),
 ], pairs=[("duplicate", 2, 3), ("conflict", 4, 5)]),
 dict(title="Gym Membership App", style="bullet", reqs=[
  ("Members can purchase or renew a membership in the app.", "F", ""),
  ("Members can book a class up to 7 days in advance.", "F", ""),
  ("A class booking can be cancelled up to 2 hours before the class starts.", "BR", ""),
  ("Members get a discount if they refer a friend.", "BR", "I"),
  ("The app should look modern.", "NF", "AN"),
  ("The front desk can check a member in by scanning a QR code.", "F", ""),
  ("The app depends on the turnstile vendor's API for door access.", "D", ""),
  ("Does the gym want to support family plans?", "Q", ""),
 ], pairs=[]),
 dict(title="Telemedicine Platform", style="num", reqs=[
  ("Patients can start a video consultation with an available doctor.", "F", ""),
  ("Video quality must adapt to the patient's bandwidth.", "NF", "A"),
  ("Doctors can write and send e-prescriptions.", "F", ""),
  ("Consultation recordings are never stored.", "C", ""),
  ("Consultation recordings are stored for 5 years.", "C", ""),
  ("The platform must be HIPAA compliant.", "C", ""),
  ("Patients are charged after the consultation.", "BR", "I"),
  ("The platform should be available at all times.", "NF", "AN"),
 ], pairs=[("conflict", 4, 5)]),
 dict(title="Customer Relationship Management", style="prose", reqs=[
  ("Sales staff can create and update customer contacts.", "F", ""),
  ("Sales staff can record every interaction with a customer.", "F", ""),
  ("The system should integrate with other tools.", "D", "AI"),
  ("Managers can view a pipeline of open deals by stage.", "F", ""),
  ("Deals above 10 lakh rupees need director approval.", "BR", ""),
  ("The CRM must be fast.", "NF", "AN"),
  ("Duplicate contacts are detected on import.", "F", "I"),
  ("Assumption: the sales team already uses the corporate email system.", "AS", ""),
 ], pairs=[]),
 dict(title="Parking Management", style="bullet", reqs=[
  ("Drivers can reserve a parking space for a chosen time window.", "F", ""),
  ("The entry gate opens automatically when it reads a valid reservation.", "F", ""),
  ("Parking is charged per hour.", "BR", "I"),
  ("The maximum stay is 12 hours.", "BR", ""),
  ("The maximum stay is 24 hours.", "BR", ""),
  ("Number plate recognition must work in poor lighting.", "NF", "AN"),
  ("The system depends on the camera vendor's recognition software.", "D", ""),
  ("What happens to a vehicle that overstays?", "Q", ""),
 ], pairs=[("conflict", 4, 5)]),
 dict(title="Recruitment Portal", style="num", reqs=[
  ("Candidates can create a profile and upload a resume.", "F", ""),
  ("Recruiters can post jobs and review applications.", "F", ""),
  ("Candidates are shortlisted automatically.", "F", "AI"),
  ("Candidates must be told the status of their application within 14 days.", "BR", ""),
  ("The portal should be easy to use.", "NF", "AN"),
  ("Candidate data must be deleted when a candidate requests it.", "C", ""),
  ("Candidates can create an account and submit a resume.", "F", ""),
  ("The portal depends on the company career site for hosting.", "D", ""),
 ], pairs=[("duplicate", 1, 7)]),
 dict(title="Utility Billing", style="prose", reqs=[
  ("Meter readings are uploaded daily by field staff.", "F", ""),
  ("Bills are generated every month from the meter readings.", "F", ""),
  ("Customers can pay bills online.", "F", "I"),
  ("Late payments incur a penalty of 2% per month.", "BR", ""),
  ("The bill generation run must complete within 4 hours for 500,000 customers.", "NF", ""),
  ("The system should be scalable.", "NF", "AN"),
  ("The billing system depends on the meter data management system.", "D", ""),
  ("Assumption: tariffs change at most once a year.", "AS", ""),
 ], pairs=[]),
 dict(title="Newsletter Platform", style="bullet", reqs=[
  ("Editors can compose and schedule newsletters.", "F", ""),
  ("Subscribers can unsubscribe with a single click.", "F", ""),
  ("Subscribers must confirm their email address before receiving newsletters.", "BR", ""),
  ("Emails should be delivered quickly.", "NF", "AN"),
  ("The platform must send at most 1 newsletter per week to a subscriber.", "BR", ""),
  ("The platform must send at least 3 newsletters per week to a subscriber.", "BR", ""),
  ("Analytics are available for each newsletter.", "F", "I"),
  ("The platform depends on a third party email service.", "D", ""),
 ], pairs=[("conflict", 5, 6)]),
]


def render(doc):
    reqs = doc["reqs"]
    texts = [r[0] for r in reqs]
    style = doc["style"]
    if style == "num":
        body = "\n".join(f"REQ-{i:02d}: {t}" for i, t in enumerate(texts, 1))
    elif style == "bullet":
        body = "\n".join(f"- {t}" for t in texts)
    else:
        groups = [texts[i:i + 3] for i in range(0, len(texts), 3)]
        body = "\n\n".join(" ".join(g) for g in groups)
    return f"{doc['title']}\n\n{body}\n"


def main():
    os.makedirs("data/eval/docs", exist_ok=True)
    os.makedirs("data/eval/gold", exist_ok=True)
    for n, doc in enumerate(DOCS, 1):
        name = f"eval_{n:02d}"
        text = render(doc)
        gold = {"doc": f"{name}.txt", "title": doc["title"], "requirements": [], "issues": []}
        for i, (t, ty, flags) in enumerate(doc["reqs"], 1):
            assert t in text, (name, t)
            gold["requirements"].append({"id": f"G{i}", "quote": t, "type": T[ty]})
            for f in flags:
                gold["issues"].append({"kind": K[f], "req_ids": [f"G{i}"]})
        for kind, a, b in doc["pairs"]:
            gold["issues"].append({"kind": kind, "req_ids": [f"G{a}", f"G{b}"]})
        with open(f"data/eval/docs/{name}.txt", "w", encoding="utf-8") as f:
            f.write(text)
        with open(f"data/eval/gold/{name}.json", "w", encoding="utf-8") as f:
            json.dump(gold, f, indent=2, ensure_ascii=False)
    print(f"wrote {len(DOCS)} documents and gold files")


if __name__ == "__main__":
    main()
