#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

samples=(
  "My name is Maya Patel, I work at Northstar Clinic in Denver, and I feel scared."
  "I am Jordan Lee, a teller at Finley Bank in Portland, and I am panicking because I misplaced account 4419-7782."
  "My daughter Emma, who is 11, was diagnosed at Cedar Ridge Pediatrics last Tuesday, and I feel helpless."
  "I live at 48 Maple Street in Queens and my landlord Victor keeps showing up at night, which makes me anxious."
  "My husband Daniel lost his job at Apex Robotics in Austin on April 4, and I am terrified about our mortgage."
  "I borrowed $7,500 from my sister Priya and now she is threatening to sue me in Cook County next month."
  "I am a nurse at St. Agnes Hospital in Baltimore, and I made a medication error on patient MRN 998231."
  "My boss Rachel at Northwind Logistics texted me at 2am and I feel trapped because she controls my visa paperwork."
  "I saw my therapist Dr. Mehta on Friday about my relapse, and I am ashamed that my partner Luis found out."
  "My son Oliver was suspended from Lincoln High after a fight with Marcus, and I am furious at the principal."
  "I used my Chase card ending in 2210 for my father's treatment at Valley Oncology, and now I cannot pay rent."
  "I am 29, pregnant, and hiding it from my manager Denise at Greenleaf Market because I think she will fire me."
  "My ex Carla keeps emailing my work address at Brighton Legal, and I feel unsafe going to the office."
  "I missed my immigration hearing in San Jose on May 8 because my car broke down, and I feel desperate."
  "My brother Aaron overdosed in our apartment on Pine Avenue, and I cannot stop replaying what happened."
  "I teach at Roosevelt Elementary in Tampa, and a parent named Melissa accused me of hurting her child."
  "My partner Noah found messages from Kai on my phone, and I feel guilty but also relieved the secret is out."
  "I was pulled over on I-95 near Richmond with my cousin Devon, and the police found pills in his backpack."
  "My mom Linda has dementia and wandered away from Sunrise Memory Care in Mesa, and I am angry at the staff."
  "I work for HelioTech in Seattle, and after reporting payroll fraud to HR I think my director Amara is retaliating."
)

for index in "${!samples[@]}"; do
  sample="${samples[$index]}"
  printf '\n===== Sample %02d/%02d =====\n' "$((index + 1))" "${#samples[@]}"
  printf '%s\n\n' "$sample"
  swift run sentiment-cli --raw "$sample"
done
