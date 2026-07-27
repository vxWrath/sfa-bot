# Bot Command Reference

## Format Legend

```
/Command *RequiredSelectionOption(Role/Member):SelectionOptionsA,B,C,ETC RequiredInputOption(Role/Member)*
         *OptionalSelectionOption(Role/Member):SelectionOptionsA,B,C,ETC OptionalInputOption(Role/Member)*
Description
```

**REQUIREMENTS:** *(strikethrough means all roles except the specified)*
`TEAMOWNER`, `COACH`, `PREMIUM`, `STAFFONLY(STATS, MEDIA/STREAMER, MODS, JUSTICE)`, `COMMISSIONERONLY(VICE)`

> If no roles are specified, the command should be executable by everyone.

---

## Commands

**1. `/aboutmember` *member(Member)***
Displays information about the inputted member, including join date, team history, linked Roblox accounts, and disciplinary history/status (suspended, blacklisted, expelled).

**2. `/aboutroblox` *username***
Same as `/aboutmember`; functions as a reverse search for suspected alting (allows checking whether someone with a specific username has ever been verified in the server).

**3. `/appoint` *team(Role) member(Member)***  `COMMISSIONERONLY(VICE)`
Appoints a candidate to team ownership. Equal chance for all non-boosters/non-donators and boosters/donators of the same tier, then priority as follows: Booster < Donator T1 < Donator T2 < Donator T3. Candidates of lower tiers have a 0% chance of receiving a franchise offer (FO) randomly until all candidates of higher tiers no longer have the candidate role.
*Example: If one Donator T3 has candidate status, they will automatically get the next random appointment selection (100% chance); after that, lower tiers have a chance.*

**4. `/forceappoint` *team(Role) member(Member)***  `COMMISSIONERONLY`
Appoints anyone to team ownership. For use only in specific situations where someone needs to bypass the normal selection process.

**5. `/award` *member(Member) award(Role):Champion,MVP,Stellar,Legend,Pro select:Add,Remove quantity***  `COMMISSIONERONLY`
Adds/removes awards to/from a member. (Stellar, Legend, and Pro are All-Pro–type awards that will have separate roles.)

**6. `/closestats` *reason***  `STAFFONLY(STATS)`
Closes the stats thread it is run in.

**7. `/color` *color(Role):ColorRolesInTheServer(NotMadeYet)***  `PREMIUM`
Adds/removes a specified color role.

**8. `/creatematchup` *team1(Role) team2(Role) create_thread:Yes,No***  `COMMISSIONERONLY`
Manually creates a matchup in the current series.

**9. `/deletematchup` *team1(Role) team2(Role) delete_thread:Yes,No***  `COMMISSIONERONLY`
Manually deletes a matchup in the current series.

**10. `/demand`**  ~~`TEAMOWNER`~~ *(everyone except Team Owner)*
Removes any team/coach roles from the user.

**11. `/demote` *member(Member)***  `TEAMOWNER`
Demotes a team member from their coaching rank.

**12. `/disband` *team(Role) reason***  `COMMISSIONERONLY(VICE)`
Disbands a team: removes coach/team owner roles from all members with the specified team role, suspends/blacklists the team owner for 2 seasons, then removes the specified team role from all members in the server.

**13. `/forcegametime` *opponent(Role) time day:Today,Tomorrow***  `TEAMOWNER, COACH`
Forces a gametime (only works if the opponent role selected and the user's role have an existing matchup). Sends a message with gametime and teams involved to the scheduling thread and gametimes channel.

**14. `/gametime` *opponent(Role) time day:Today,Tomorrow***  `TEAMOWNER, COACH`
Suggests a gametime (only works if the opponent role selected and the user's role have an existing matchup). Sends a confirmation message in the scheduling thread for the opposing team to accept/deny; if accepted, sends a message with gametime and teams involved to the scheduling thread and gametimes channel.

**15. `/lfp` *message***  `TEAMOWNER, COACH`
Sends the message to the LFP (Looking For Players) channel with info on who sent it.

**16. `/mediaping`**  `STAFFONLY(MEDIA)`
@Mentions the Media Ping role in the channel it is run in (media-designated channels only, NOT debate). 2-hour cooldown per ping per channel (timers run independently for each media channel).

**17. `/members` *role(Role)***
Displays all members that have the selected role. Special format if the role is a team role: displays Team Owner/coaches separately, then the players below, and includes total ring/award count for players.

**18. `/mute` *member(Member) duration:1m,5m,10m,30m,1h,2h,12h,1d,7d reason***  `STAFFONLY(MODS)`
Times out the selected member for the selected duration.

**19. `/nextround`**  `COMMISSIONERONLY`
Advances to the next round of playoffs.

**20. `/nextseason`**  `COMMISSIONERONLY`
Moves the league into the next season.

**21. `/nextseries`**  `COMMISSIONERONLY`
Advances the league to the next series.

**22. `/offer` *member(Member) contract*** *(entry cut off in source document  description not provided)*

---

*Note: The source document ends mid-entry at command #22 (`/offer`). If you have the rest of the list, send it over and I'll continue formatting from there.*