"""Small static-map A* demonstration; not a replacement for Nav2."""
import heapq,math,re

def astar(grid,start,goal):
    h,w=grid.shape
    def free(c):return 0<=c[0]<w and 0<=c[1]<h and grid[c[1],c[0]]==0
    if not free(start) or not free(goal):raise ValueError('Start or goal is occupied, unknown, or outside the map.')
    def heuristic(c):
        dx,dy=abs(c[0]-goal[0]),abs(c[1]-goal[1])
        return max(dx,dy)+(math.sqrt(2)-1)*min(dx,dy)
    q=[(heuristic(start),heuristic(start),0,start)];cost={start:0};parent={}
    while q:
        _,_,g,c=heapq.heappop(q)
        if g>cost[c]+1e-12:continue
        if c==goal:
            route=[c]
            while c!=start:c=parent[c];route.append(c)
            return route[::-1]
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
            n=(c[0]+dx,c[1]+dy)
            if not free(n):continue
            # A diagonal cannot squeeze between touching obstacles.
            if dx and dy and not (free((c[0]+dx,c[1])) and free((c[0],c[1]+dy))):continue
            ng=g+(math.sqrt(2) if dx and dy else 1)
            if ng+1e-12<cost.get(n,math.inf):
                cost[n]=ng;parent[n]=c
                hscore=heuristic(n);heapq.heappush(q,(ng+hscore,hscore,ng,n))
    raise ValueError('No route through known free space.')

def segment_is_free(grid,start,end):
    """Check every crossed cell, including both sides of diagonal corner crossings.

    Points are continuous grid coordinates (cell centres have a .5 fraction).
    Unknown space is blocked. DDA traversal avoids sparse-sampling gaps.
    """
    if not all(math.isfinite(v) for v in (*start,*end)):return False
    h,w=grid.shape
    def free(x,y):return 0<=x<w and 0<=y<h and grid[y,x]==0
    x,y=map(math.floor,start);gx,gy=map(math.floor,end)
    if not free(x,y) or not free(gx,gy):return False
    dx,dy=end[0]-start[0],end[1]-start[1]
    sx=1 if dx>0 else -1 if dx<0 else 0;sy=1 if dy>0 else -1 if dy<0 else 0
    tx=((x+1-start[0])/dx if dx>0 else (start[0]-x)/-dx if dx<0 else math.inf)
    ty=((y+1-start[1])/dy if dy>0 else (start[1]-y)/-dy if dy<0 else math.inf)
    dtx=1/abs(dx) if dx else math.inf;dty=1/abs(dy) if dy else math.inf
    # If travelling exactly along a cell boundary, check both touching rows/columns.
    edge_x=dx==0 and abs(start[0]-round(start[0]))<1e-12
    edge_y=dy==0 and abs(start[1]-round(start[1]))<1e-12
    def clear(cx,cy):
        return free(cx,cy) and (not edge_x or free(cx-1,cy)) and (not edge_y or free(cx,cy-1)) and (not (edge_x and edge_y) or free(cx-1,cy-1))
    if not clear(x,y):return False
    while (x,y)!=(gx,gy):
        if min(tx,ty)>=1-1e-12:
            # A negative-direction endpoint on an integer boundary belongs to
            # the higher cell; do not step beyond it and overshoot that cell.
            if abs(tx-ty)<1e-12 and (not free(x+sx,y) or not free(x,y+sy)):return False
            return clear(gx,gy)
        if abs(tx-ty)<1e-12:
            if not free(x+sx,y) or not free(x,y+sy):return False
            x+=sx;y+=sy;tx+=dtx;ty+=dty
        elif tx<ty:x+=sx;tx+=dtx
        else:y+=sy;ty+=dty
        if not clear(x,y):return False
    return True

def plan_route(grid,start,goal,resolution,origin=(-20.,-20.)):
    """Eight-neighbour A* with checked shortcuts and exact world endpoints.

    Direct clear routes use the Euclidean shortest segment. Obstacle detours are
    grid-optimal before greedy shortcutting, not globally optimal continuous paths.
    """
    def to_grid(p):return ((p[0]-origin[0])/resolution,(p[1]-origin[1])/resolution)
    def to_world(c):return (origin[0]+(c[0]+.5)*resolution,origin[1]+(c[1]+.5)*resolution)
    a,b=to_grid(start),to_grid(goal)
    if segment_is_free(grid,a,b):return [tuple(start),tuple(goal)]
    cells=astar(grid,tuple(map(math.floor,a)),tuple(map(math.floor,b)))
    points=[tuple(start)]+[to_world(c) for c in cells]+[tuple(goal)]
    route=[points[0]];index=0
    while index<len(points)-1:
        next_index=len(points)-1
        while next_index>index and not segment_is_free(grid,to_grid(points[index]),to_grid(points[next_index])):next_index-=1
        if next_index==index:raise ValueError('No clear segment connects the exact start or destination to the route.')
        route.append(points[next_index]);index=next_index
    return route

def route_length(route):return sum(math.dist(a,b) for a,b in zip(route,route[1:]))

def navigation_intent(text,landmarks):
    """Bounded simulation skills, including ordered 'then' sequences."""
    t=re.sub(r'\s+',' ',text.strip().lower().rstrip('.!?'))
    t=re.sub(r'^(?:can you |could you |please )+','',t)
    parts=re.split(r'\s*,?\s+(?:and then|then)\s+',t)
    if len(parts)>1:
        if len(parts)>8:raise ValueError('Use at most eight steps per simulation request.')
        steps=[_single_intent(p,landmarks) for p in parts]
        if any(s is None or s['action'] not in ('goal','forward','backward','turn') for s in steps):
            raise ValueError('Sequences support mapped goals, forward/backward distances and turns only.')
        return {'action':'sequence','steps':steps}
    return _single_intent(t,landmarks)

def _single_intent(t,landmarks):
    """Explicit requests only; no invented object/person positions."""
    t=t.strip().rstrip('.!?')
    if t in ('stop','stop navigation','cancel navigation','cancel','stop moving'):return {'action':'stop'}
    if t in ('list waypoints','show waypoints','what are the waypoints'):return {'action':'list_waypoints'}
    number=r'-?\d+(?:\.\d+)?'
    match=re.fullmatch(r'(?:save|set|add) waypoint ([a-z][a-z0-9_]{0,31})(?: at)? (here|'+number+r'[,\s]+\s*'+number+r')',t)
    if match:
        if match[1] in ('start','goal_a'):raise ValueError('The built-in start and goal_a waypoints cannot be replaced.')
        xy=None if match[2]=='here' else [float(v) for v in re.split(r'[,\s]+',match[2])]
        return {'action':'save_waypoint','name':match[1],'xy':xy}
    match=re.fullmatch(r'(?:go|navigate|move|drive)(?: to)? (?:the |waypoint )?([a-z][a-z0-9_]{0,31})',t)
    if match and match[1] in landmarks:return {'action':'goal','name':match[1],'xy':landmarks[match[1]]}
    match=re.fullmatch(r'(?:go|move|drive) (forward|backward|backwards|back) (\d+(?:\.\d+)?)\s*(?:m|meter|meters|metre|metres)',t)
    if match:
        distance=float(match[2])
        if not 0<distance<=5:raise ValueError('Use a distance greater than zero and at most 5 metres.')
        return {'action':'forward' if match[1]=='forward' else 'backward','distance':distance}
    match=re.fullmatch(r'(?:spin|rotate|turn)(?: (left|right|clockwise|counterclockwise|anticlockwise))? (\d+(?:\.\d+)?)\s*(?:degrees?|deg|°)(?: (left|right|clockwise|counterclockwise|anticlockwise))?',t)
    if match:
        degrees=float(match[2]);direction=match[1] or match[3] or 'left'
        if match[1] and match[3] and match[1]!=match[3]:raise ValueError('Specify one turn direction.')
        if not 0<degrees<=360:raise ValueError('Use a turn greater than zero and at most 360 degrees.')
        return {'action':'turn','degrees':degrees*(-1 if direction in ('right','clockwise') else 1)}
    if t in ('turn left','turn right','turn around','spin around'):
        return {'action':'turn','degrees':{'turn left':90,'turn right':-90,'turn around':180,'spin around':360}[t]}
    match=re.fullmatch(r'(?:go|navigate|move|drive) to (?:x\s*)?(-?\d+(?:\.\d+)?)[,\s]+(?:y\s*)?(-?\d+(?:\.\d+)?)',t)
    if match:return {'action':'goal','xy':[float(match[1]),float(match[2])]}
    if re.match(r'^(?:go|navigate|move|drive|spin|turn|rotate|save waypoint|set waypoint|add waypoint|stop navigation|cancel navigation)\b',t):
        raise ValueError('Specify a saved waypoint, go to 2, 3, go forward 1 metre, turn right 90 degrees, or spin 360 degrees. Save a destination with save waypoint desk at 2, 3. People/objects are not mapped.')
    return None
