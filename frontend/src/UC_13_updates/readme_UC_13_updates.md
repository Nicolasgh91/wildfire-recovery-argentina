The refactor of the fire components to match the new design requirements with proper API integration, severity logic, and the specified visual style. Let me first check the current implementation:

Now I have the full context. I'll implement the new component architecture with:

1. TypeScript interfaces matching the API schema
2. Helper function for severity logic based on FRP
3. Updated FireCard with the new design
4. Enhanced FireFilters with CSV export and more options
5. Updated FireGridPage with API integration, skeleton loading, and URL params


Created Pagination componentNow let me create the main FireGridPage that handles state, API integration, and URL params:

Created FireGridPageCreated loading fileNow let me update the existing home page to link to the new fires grid page and update the navbar to include this new route:

Read navbarAdded Fires link to navbarAdded Fires nav itemv2[data-radix-scroll-area-viewport]{scrollbar-width:none;-ms-overflow-style:none;-webkit-overflow-scrolling:touch;}[data-radix-scroll-area-viewport]::-webkit-scrollbar{display:none}
  
  
  navbar.tsxcomponents/navbar.tsxI've created the complete FireGridPage implementation with the following components:

1. **`/types/fire.ts`** - TypeScript interfaces matching the FastAPI Pydantic schema (`FireEventListItem`, `PaginationMeta`, `FireListResponse`) plus the `getSeverityConfig()` helper function that maps FRP values to severity labels and Tailwind classes.
2. **`/components/fires/fire-card.tsx`** - Presentational card component with the specified design: gradient background, central flame icon, severity/status badges, metadata row with icons, and "Ver Detalles" button. Includes a `FireCardSkeleton` for loading states.
3. **`/components/fires/fire-filters.tsx`** - Responsive filter bar with search input, province dropdown, sort selector, advanced filters (date range, active-only toggle), and CSV export button.
4. **`/components/fires/pagination.tsx`** - Full pagination component with page numbers, navigation arrows, page size selector, and results info.
5. **`/app/fires/page.tsx`** - Main container using SWR for data fetching, URL query params for shareable filter state, skeleton loading grid, error handling with retry, and empty state display.
