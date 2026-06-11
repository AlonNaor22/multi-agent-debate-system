/**
 * Centralized user-facing UI copy.
 *
 * Every literal string the user reads — headings, buttons, placeholders, empty
 * states, and client-facing error messages — lives here so the UI text is
 * defined in exactly one place. Adding another language later becomes a
 * drop-in: swap or wrap this module rather than hunting through components.
 *
 * Intentionally NOT here: domain tokens that mirror backend enum values (the
 * PRO / CON / TIE side labels and the speaker badges), console/dev log text,
 * and anything the user never sees.
 */
export const strings = {
  common: {
    versus: 'vs',
  },
  setup: {
    title: 'Multi-Agent Debate System',
    tagline: 'Watch AI agents debate any topic with different personalities',
    viewPastDebates: '📜 View past debates',
    topicLabel: 'Debate Topic',
    topicPlaceholder: 'e.g., Should artificial intelligence be regulated by governments?',
    topicRequired: 'Please enter a debate topic',
    proStyleHeading: 'PRO Agent Style',
    conStyleHeading: 'CON Agent Style',
    startDebate: 'Start Debate',
    startingDebate: 'Starting Debate...',
  },
  chat: {
    newDebate: 'Start New Debate',
    typing: 'typing...',
  },
  // The six display steps the progress bar collapses the nine phases into.
  progress: {
    introduction: 'Introduction',
    openings: 'Openings',
    rebuttals: 'Rebuttals',
    closings: 'Closings',
    verdict: 'Verdict',
    scoring: 'Scoring',
  },
  scoreboard: {
    heading: 'Argument Scores',
    average: 'avg',
    noArguments: 'No arguments scored.',
    strongestArgument: 'Strongest argument: ',
    weakestArgument: 'Weakest argument: ',
    tie: "It's a tie",
    wins: (winner: string) => `${winner} wins`,
  },
  voting: {
    title: 'Audience Vote',
    prompt: 'Who is winning the debate so far?',
    proWinning: 'PRO is winning',
    conWinning: 'CON is winning',
    tie: "It's a tie",
  },
  pastDebates: {
    title: 'Past Debates',
    newDebate: '+ New Debate',
    backToList: '← Back to list',
    loading: 'Loading…',
    empty: "No debates yet — start one and it'll show up here.",
    loadListError: 'Could not load past debates.',
    loadDetailError: 'Could not load that debate.',
    messageCount: (count: number) => `· ${count} messages`,
    tie: 'Tie',
    won: (winner: string) => `${winner} won`,
  },
  errors: {
    createDebate: 'Failed to create debate',
    websocket: 'WebSocket connection failed',
    generic: 'An error occurred',
  },
} as const;
