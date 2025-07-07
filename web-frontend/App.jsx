import { useState } from 'react'
import PropTypes from 'prop-types';
import './App.css'


const NavItem = ({ title, items }) => {
    const [isOpen, setIsOpen] = useState(false);
    return (
        <div
            className="nav-item"
            onMouseEnter={() => setIsOpen(true)}
            onMouseLeave={() => setIsOpen(false)}
        >
            <span>{title}</span>
            {items && isOpen && (
                <div className="dropdown">
                    {items.map((item, index) => (
                        <a key={index} href={item.link}>{item.name}</a>
                    ))}
                </div>
            )}
        </div>
    );
};

NavItem.propTypes = {
    title: PropTypes.string.isRequired,
    items: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        link: PropTypes.string.isRequired
    }))
};

const GameScroller = () => {
    // Sample game data - replace this with actual data fetching later
    const games = [
        { id: 1, time: '7:00 PM', homeTeam: 'Lakers', awayTeam: 'Celtics', homeScore: 0, awayScore: 0 },
        { id: 2, time: '7:30 PM', homeTeam: 'Warriors', awayTeam: 'Suns', homeScore: 0, awayScore: 0 },
        { id: 3, time: '8:00 PM', homeTeam: 'Bucks', awayTeam: 'Heat', homeScore: 0, awayScore: 0 },
        { id: 4, time: '8:30 PM', homeTeam: 'Mavs', awayTeam: 'Spurs', homeScore: 0, awayScore: 0 },
        { id: 5, time: '9:00 PM', homeTeam: 'Nuggets', awayTeam: 'Clippers', homeScore: 0, awayScore: 0 },
    ];

    return (
        <div className="game-scroller-container">
            <div className="current-games-label">Current Games</div>
            <div className="game-scroller">
                {games.map((game) => (
                    <div key={game.id} className="game-item">
                        <div className="game-time">{game.time}</div>
                        <div className="game-teams">
                            <span>{game.awayTeam}</span>
                            <span className="score">{game.awayScore}</span>
                            <span>@</span>
                            <span>{game.homeTeam}</span>
                            <span className="score">{game.homeScore}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

const LeagueTable = ({ leagueName, data, color }) => {
    return (
        <div className="league-table-container">
            <table className="league-table">
                <thead style={{ backgroundColor: color }}>
                    <tr className="league-header">
                        <th colSpan="9">{leagueName}</th>
                    </tr>
                    <tr>
                        <th>#</th>
                        <th>TEAM</th>
                        <th>W</th>
                        <th>L</th>
                        <th>T</th>
                        <th>PCT</th>
                        <th>PF</th>
                        <th>PA</th>
                        <th>STRK</th>
                    </tr>
                </thead>
                <tbody>
                    {data.slice(0, 10).map((team, index) => (
                        <tr key={team.name}>
                            <td>{index + 1}</td>
                            <td>{team.name}</td>
                            <td>{team.wins}</td>
                            <td>{team.losses}</td>
                            <td>{team.ties}</td>
                            <td>{team.pct}</td>
                            <td>{team.pf}</td>
                            <td>{team.pa}</td>
                            <td>{team.streak}</td>
                        </tr>
                    ))}
                </tbody>
                <tfoot style={{ backgroundColor: color }}>
                    <tr className="league-footer">
                        <td colSpan="9"></td>
                    </tr>
                </tfoot>
            </table>
        </div>
    );
};

const leagueData = [
    {
        name: 'NFL',
        color: '#013369',
        updateIndex: 1,
        data: [
            { name: 'Chiefs', wins: 4, losses: 0, ties: 0, pct: '1.000', pf: 92, pa: 72, streak: 'W4' },
            // ... add more teams
        ]
    },
    {
        name: 'MLB',
        color: '#041E42',
        updateIndex: 2,
        data: [
            { name: 'Yankees', wins: 4, losses: 0, ties: 0, pct: '1.000', pf: 92, pa: 72, streak: 'W4' },
            // ... add MLB data
        ]
    },
    {
        name: 'MLS',
        color: '#27A745',
        updateIndex: 3,
        data: [
            { name: 'Red Bulls', wins: 4, losses: 0, ties: 0, pct: '1.000', pf: 92, pa: 72, streak: 'W4' },
            // ... add MLS data
        ]
    },
    {
        name: 'NHL',
        color: '#000000',
        updateIndex: 4,
        data: [
            { name: 'Rangers', wins: 4, losses: 0, ties: 0, pct: '1.000', pf: 92, pa: 72, streak: 'W4' },
            // ... add NHL data
        ]
    },
    {
        name: 'NBA',
        color: '#C9082A',
        updateIndex: 5,
        data: [
            { name: 'Celtics', wins: 4, losses: 0, ties: 0, pct: '1.000', pf: 92, pa: 72, streak: 'W4' },
            // ... add NBA data
        ]
    }
];

LeagueTable.propTypes = {
    leagueName: PropTypes.string.isRequired,
    data: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        wins: PropTypes.number.isRequired,
        losses: PropTypes.number.isRequired,
        ties: PropTypes.number.isRequired,
        pct: PropTypes.string.isRequired,
        pf: PropTypes.number.isRequired,
        pa: PropTypes.number.isRequired,
        streak: PropTypes.string.isRequired
    })).isRequired,
    color: PropTypes.string.isRequired
};
function App() {
    const sortedLeagueData = leagueData.sort((a, b) => a.updateIndex - b.updateIndex);
    const navItems = [
        {
            title: "Leagues",
            items: [
                { name: "NFL", link: "/leagues/nfl" },
                { name: "NBA", link: "/leagues/nba" },
                { name: "MLB", link: "/leagues/mlb" },
                { name: "NHL", link: "/leagues/nhl" },
                { name: "MLS", link: "/leagues/mls" },
            ]
        },
        {
            title: "Standings",
            items: [
                { name: "NFL", link: "/standings/nfl" },
                { name: "NBA", link: "/standngs/nba" },
                { name: "MLB", link: "/standings/mlb" },
                { name: "NHL", link: "/standings/nhl" },
                { name: "MLS", link: "/standings/mls" },
            ]
        },
        {
            title: "Brackets",
            items: [
                { name: "NFL", link: "/Brackets/nfl" },
                { name: "NBA", link: "/Brackets/nba" },
                { name: "MLB", link: "/Brackets/mlb" },
                { name: "NHL", link: "/Brackets/nhl" },
                { name: "MLS", link: "/Brackets/mls" },
            ]
        },
        {
            title: "Best Odds",
            items: [
                { name: "Today's Picks", link: "/best-bets/today" },
                { name: "Weekly Roundup", link: "/best-bets/weekly" },
                { name: "Wild Cards", link: "/best-bets/wild-cards" },
            ]
        },
        {
            title: "History",
            items: [
                { name: "Past Standings", link: "/history/predictions" },
                { name: "Performance Stats", link: "/history/stats" },
                { name: "Misc", link: "/history/misc" },
            ]
        },
        { title: "About", items: null },
    ];

    return (
        <div className="app">
            <header className="app-header">
                <div className="logo">Yoffsornah.com</div>
                <nav className="main-nav">
                    {navItems.map((item, index) => (
                        <NavItem key={index} title={item.title} items={item.items} />
                    ))}
                </nav>
            </header>
            <GameScroller />
            <main className="app-main">
                <h1 className="centered-heading">Welcome to Yoffsornah.com</h1>
                <p className="centered-text">Your innovative, live* sports season prediction tool!</p>
                {/* Main content will go here */}
                <h2 className="centered-heading">Latest Updates</h2>
                <div className="league-tables-container">
                    {sortedLeagueData.map((league) => (
                        <LeagueTable
                            key={league.name}
                            leagueName={league.name}
                            data={league.data}
                            color={league.color}
                        />
                    ))}
                </div>
            </main>
            <footer className="app-footer">
                <p>&copy; 2023 Yoffsornah.com. All rights reserved.</p>
            </footer>
        </div>
    );
}

export default App;
