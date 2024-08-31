from Pygen import UI, Events, TileMap, Sprites, Animator
import pygame, time, math, random, json
from enum import Enum

pygame.init()

# =============================================================================
#                               Enums
#=============================================================================


# the players animation states
class PlayerStates (Enum):
    walkingLeft = 0
    walkingRight = 1
    idle = 3

# the states of animation for a zombie
class EnemyAnimationStates (Enum):
    walkingLeft = 0
    walkingRight = 1


# the classes of mobs/player used to detect who should take damage
class Friendlies (Enum):
    friendly = 0
    enemy = 1


# amo types
class AmoType (Enum):
    Pistol = 0
    LargeRifle = 1
    Shotgun = 2
    Rifle = 3

# drop types
class DropTypes (Enum):
    Weapon = 0
    Amo = 1
    Part = 2
    Armor = 3


# =============================================================================
#                               Light Objects
#=============================================================================


# stores a radial light sprite
class RadialLight:
    def __init__(self, radius: int, color: tuple, step: int, renderShadows: bool=True) -> None:
        # storing the inputed parameters
        self.radius = radius
        self.color = color
        self.step = step
        self.renderShadows = renderShadows

        # generating the radia light
        self.surface = pygame.Surface([radius*2, radius*2])
        for r in range(radius, 0, -step):
            brightness = pow(1-r/radius, 2)
            pygame.draw.circle(self.surface, (color[0] * brightness, color[1] * brightness, color[2] * brightness), [radius, radius], r)
    
    # rendering the radial light
    def Render(self, lightMap: pygame.Surface, pos: tuple) -> None:
        transPos = [pos[0] - cameraPos[0] + screenSize[0]//2, pos[1] - cameraPos[1] + screenSize[1]//2]
        if not self.renderShadows:
            lightMap.blit(self.surface, [round(transPos[0] - self.radius), round(transPos[1] - self.radius)], special_flags=pygame.BLEND_ADD)
            return
        
        # rendering the light
        lightFeild = pygame.Surface([self.radius*2, self.radius*2])
        lightFeild.blit(self.surface, [0, 0])
        for obj in solidObjects:
            obj.RenderShadow(lightFeild, pos, self.radius)
        lightMap.blit(lightFeild, [round(transPos[0] - self.radius), round(transPos[1] - self.radius)], special_flags=pygame.BLEND_ADD)


# a light with a fixed position
class Light (RadialLight):
    def __init__(self, radius: int, color: tuple, step: int, renderShadows: bool, pos: tuple) -> None:
        super().__init__(radius, color, step, renderShadows=renderShadows)
        self.pos = pos
    def Render(self, lightMap: pygame.Surface) -> None:
        super().Render(lightMap, self.pos)


# a solid object that casts shadows
class ShadowedObject:
    def __init__(self, pos: tuple, size: tuple, sprite: pygame.Surface=None, renderShadows: bool=True, renderObject: bool=True, collideable: bool=True) -> None:
        self.pos = pos
        self.size = size

        self.renderShadows = renderShadows
        self.renderObject = renderObject
        self.collideable = collideable

        self.sprite = sprite
        if not self.sprite:
            self.sprite = pygame.Surface(self.size)
            self.sprite.fill((0, 225, 0))
        
        # getting the length from center to the outside of the object
        self.totalLength = (self.size[0]//2)**2 + (self.size[1]//2)**2
        self.centerPosition = [self.pos[0] + self.size[0]//2, self.pos[1] + self.size[1]//2]
    
    # checks collision wiht a given point
    def CheckCollision(self, point: tuple) -> bool:
        return self.collideable and point[0] >= self.pos[0] and point[0] <= self.pos[0] + self.size[0] and point[1] >= self.pos[1] and point[1] <= self.pos[1] + self.size[1]

    # rendering the object
    def Render(self, screen: pygame.Surface) -> None:
        if not self.renderObject: return  # in case it's for a hitbox and not a shadow
        position = [round(self.pos[0] - cameraPos[0] + screenSize[0]//2), round(self.pos[1] - cameraPos[1] + screenSize[1]//2)]
        screen.blit(self.sprite, position)
        #pygame.draw.rect(screen, (0, 225, 0), [self.pos[0] - cameraPos[0] + screenSize[0]//2, self.pos[1] - cameraPos[1] + screenSize[1]//2, self.size[0], self.size[1]])
    
    # renders the object's shadow
    def RenderShadow(self, lightMap: pygame.Surface, position: tuple, radius: int) -> None:
        if not self.renderShadows: return  # in case the object doesn't render shadows and is just being used as a hit box
        
        # checking if the light is within range
        dif = [self.centerPosition[0] - position[0], self.centerPosition[1] - position[1]]
        if dif[0]**2 + dif[1]**2 > radius**2+self.totalLength:
            return
        
        # getting the coners the shadow casts from
        difTL = [self.pos[0]-position[0], self.pos[1]-position[1]]
        difBR = [self.pos[0]-position[0]+self.size[0], self.pos[1]-position[1]+self.size[1]]

        points = []
        leftRightCenter = difTL[0] < 0 and difBR[0] > 0  # player is to the right of the object
        topBottomCenter = difTL[1] < 0 and difBR[1] > 0  # player is bellow object
        if leftRightCenter:
            if difTL[1] >= 0:
                # top
                points.append([self.pos[0], self.pos[1]])
                points.append([self.pos[0] + self.size[0], self.pos[1]])
            else:
                # bottom
                points.append([self.pos[0], self.pos[1] + self.size[1]-1])
                points.append([self.pos[0] + self.size[0], self.pos[1] + self.size[1]-1])
        elif topBottomCenter:
            if difTL[0] >= 0:
                # left
                points.append([self.pos[0], self.pos[1]])
                points.append([self.pos[0], self.pos[1] + self.size[1]])
            else:
                # right
                points.append([self.pos[0] + self.size[0]-1, self.pos[1]])
                points.append([self.pos[0] + self.size[0]-1, self.pos[1] + self.size[1]])
        else:
            # angle
            if difTL[0] >= 0:
                if difTL[1] >= 0:
                    # top left
                    points.append([self.pos[0], self.pos[1] + self.size[1]])
                    points.append([self.pos[0], self.pos[1]])
                    points.append([self.pos[0] + self.size[0], self.pos[1]])
                else:
                    # bottom left
                    points.append([self.pos[0] + self.size[0], self.pos[1] + self.size[1]-1])
                    points.append([self.pos[0], self.pos[1] + self.size[1]-1])
                    points.append([self.pos[0], self.pos[1]])
            else:
                if difTL[1] >= 0:
                    # top right
                    points.append([self.pos[0], self.pos[1]])
                    points.append([self.pos[0] + self.size[0]-1, self.pos[1]])
                    points.append([self.pos[0] + self.size[0]-1, self.pos[1] + self.size[1]])
                else:
                    # bottom right
                    points.append([self.pos[0], self.pos[1] + self.size[1]-1])
                    points.append([self.pos[0] + self.size[0]-1, self.pos[1] + self.size[1]-1])
                    points.append([self.pos[0] + self.size[0]-1, self.pos[1]])
        
        # projecting the points
        surfSize = radius * 2
        projectedPoints = []
        for point in points[::-1]:
            dif = [point[0] - position[0], point[1] - position[1]]
            length = math.sqrt(dif[0]**2 + dif[1]**2)
            dif = [dif[0] / length, dif[1] / length]
            projectedPoints.append([
                point[0] + dif[0]*surfSize*2,
                point[1] + dif[1]*surfSize*2
            ])
        
        points = points+projectedPoints
        points = list(map(lambda p: [p[0] - position[0] + radius, p[1] - position[1] + radius], points))
        
        # rendering the polygon
        surf = pygame.Surface((surfSize, surfSize))
        surf.fill((255, 255, 255))
        surf.set_colorkey((255, 255, 255))
        pygame.draw.polygon(surf, (0, 0, 0), points)
        pygame.draw.rect(surf, (255, 255, 255), [self.pos[0] - position[0] + radius, self.pos[1] - position[1] + radius, self.size[0], self.size[1]])
        lightMap.blit(surf, [0, 0])


# =============================================================================
#                               Map Objects
#=============================================================================


# stores a unique hitbox for a tile since they don't always take up an entire block
class HitBox:
    # initialization
    def __init__(self, pos: tuple, size: tuple) -> None:
        self.pos = pos
        self.size = size
    
    # checking for a collision
    def Collide(self, position: tuple) -> bool:
        xValid = self.pos[0] < position[0] and self.pos[0]+self.size[0] > position[0]
        yValid = self.pos[1] < position[1] and self.pos[1]+self.size[1] > position[1]
        return xValid and yValid
    
    # checking for a collision using lines
    def CollideLineHorizontal(self, xSmall: int, xLarge: int, y: int) -> None:  # sees if a horizontal line collides with the hitbox
        # check that at least 1 verticle line is inbetween the input points
        y1, y2 = self.pos[1], self.pos[1]+self.size[1]
        if y < y1 or y > y2: return  # not alligned vertically
        x1, x2 = self.pos[0], self.pos[0]+self.size[0]
        return (x1 > xSmall and x1 < xLarge) or (x2 > xSmall and x2 < xLarge) or (x1 < xSmall and x2 > xLarge)
    
    # checking for a collision using lines
    def CollideLineVerticle(self, ySmall: int, yLarge: int, x: int) -> None:  # sees if a verticle line collides with the hitbox
        # check that at least 1 horizontal line is inbetween the input points
        x1, x2 = self.pos[0], self.pos[0]+self.size[0]
        if x < x1 or x > x2: return  # not alligned horizontally
        y1, y2 = self.pos[1], self.pos[1]+self.size[1]
        return (y1 > ySmall and y1 < yLarge) or (y2 > ySmall and y2 < yLarge) or (y1 < ySmall and y2 > yLarge)


# =============================================================================
#                               Entities
#=============================================================================


# a basic entity class
class Entity:
    def __init__(self, sprite: pygame.Surface, position: list, velocity: list, collision: bool=False, light: object=None) -> None:
        self.position = position
        self.velocity = velocity
        self.sprite = sprite
        self.light = light
        self.collision = collision
    
        self.spriteSize = self.sprite.get_size()

    # updating the entity
    def Update(self, events: Events.Manager, dt: float, collidables: list=[]) -> None:
        # moving the entity
        newX = self.position[0] + self.velocity[0] * dt
        newY = self.position[1] + self.velocity[1] * dt

        # checking for collision
        spriteSize = [self.spriteSize[0]//2, self.spriteSize[1]//2]
        if self.collision:  # add tile collision here
            xValid, yValid = True, True
            
            # checking horizontal movement collision on the tile map
            hitboxes = [
                [newX-spriteSize[0], self.position[1]-spriteSize[1]],  # top left
                [newX+spriteSize[0], self.position[1]+spriteSize[1]],  # top right
                [newX-spriteSize[0], self.position[1]+spriteSize[1]],  # bot left
                [newX+spriteSize[0], self.position[1]-spriteSize[1]],  # bot right
            ]
            for x, y in hitboxes:
                hitbox = GetTileMapCollisionHitbox([x, y])  # getting the hitbox

                # getting relative coords for the tile
                basePointX = (x // tileMap.tileSize) * tileMap.tileSize
                basePointY = (y // tileMap.tileSize) * tileMap.tileSize
                if hitbox:  # checking for collisions based on all possible lines
                    if hitbox.CollideLineHorizontal(newX-spriteSize[0]-basePointX, newX+spriteSize[0]-basePointX, y-basePointY):
                        xValid = False
                    if hitbox.CollideLineVerticle(self.position[1]-spriteSize[1]-basePointY, self.position[1]+spriteSize[1]-basePointY, x-basePointX):
                        xValid = False
            
            # checking vertical movement collision on the tile map
            hitboxes = [
                [self.position[0]-spriteSize[0], newY-spriteSize[1]],  # top left
                [self.position[0]+spriteSize[0], newY+spriteSize[1]],  # top right
                [self.position[0]-spriteSize[0], newY+spriteSize[1]],  # bot left
                [self.position[0]+spriteSize[0], newY-spriteSize[1]],  # bot right
            ]
            for x, y in hitboxes:
                hitbox = GetTileMapCollisionHitbox([x, y])  # getting the hitbox

                # getting relative coords for the tile
                basePointX = (x // tileMap.tileSize) * tileMap.tileSize
                basePointY = (y // tileMap.tileSize) * tileMap.tileSize
                if hitbox:  # checking for collisions based on all possible lines
                    if hitbox.CollideLineHorizontal(self.position[0]-spriteSize[0]-basePointX, self.position[0]+spriteSize[0]-basePointX, y-basePointY):
                        yValid = False
                    if hitbox.CollideLineVerticle(newY-spriteSize[1]-basePointY, newY+spriteSize[1]-basePointY, x-basePointX):
                        yValid = False

            for obj in solidObjects + collidables:
                # checking for collisions on different parts of the entity
                if obj.CheckCollision([newX-spriteSize[0], self.position[1]+spriteSize[1]]): xValid = False
                if obj.CheckCollision([newX-spriteSize[0], self.position[1]-spriteSize[1]]): xValid = False
                if obj.CheckCollision([newX+spriteSize[0], self.position[1]-spriteSize[1]]): xValid = False
                if obj.CheckCollision([newX+spriteSize[0], self.position[1]+spriteSize[1]]): xValid = False
                
                if obj.CheckCollision([self.position[0]-spriteSize[0], newY+spriteSize[1]]): yValid = False
                if obj.CheckCollision([self.position[0]-spriteSize[0], newY-spriteSize[1]]): yValid = False
                if obj.CheckCollision([self.position[0]+spriteSize[0], newY-spriteSize[1]]): yValid = False
                if obj.CheckCollision([self.position[0]+spriteSize[0], newY+spriteSize[1]]): yValid = False
            
            # setting the position
            if xValid and yValid: self.position = [newX, newY]
            elif xValid: self.position = [newX, self.position[1]]
            elif yValid: self.position = [self.position[0], newY]
        else: self.position = [newX, newY]
    
    # checks collision with a point
    def CheckCollision(self, point: tuple) -> bool:
        pos = [self.position[0]-self.spriteSize[0]//2, self.position[1]-self.spriteSize[1]//2]
        return point[0] >= pos[0] and point[0] <= pos[0]+self.spriteSize[0] and point[1] >= pos[1] and point[1] <= pos[1]+self.spriteSize[1]

    # rendering the entity
    def Render(self, screen: pygame.Surface, lightMap: pygame.Surface, lightOffset: tuple=(0, 0)) -> None:
        # rendering the sprite
        translatedPosition = [self.position[0] - cameraPos[0] + screenSize[0]//2, self.position[1] - cameraPos[1] + screenSize[1]//2]
        width, height = self.sprite.get_size()
        screen.blit(self.sprite, [round(translatedPosition[0]-width//2), round(translatedPosition[1]-height//2)])

        # rendering the light if there is one
        if self.light: self.light.Render(lightMap, [round(self.position[0]+lightOffset[0]), round(self.position[1]+lightOffset[1])])
    
    # runs when the entity is killed
    def Kill(self) -> None:
        pass


# a class for an enemy
class Enemy (Entity):
    def __init__(self, sprites: pygame.Surface, position: list, damage: float, speed: float, health: float, drops: list, light: object=None, sparkRange: list=[3, 10], weapon: object=None, engagementDst: int = 125) -> None:
        # creating the animation for the mob          {Walking: {"speed": 1, "reset": False, sprites: [1, 2, 3, 4]}}
        animation = {
            EnemyAnimationStates.walkingRight: {"speed": 5, "reset": False, "sprites": [0, 1, 2, 3]},
            EnemyAnimationStates.walkingLeft: {"speed": 5, "reset": False, "sprites": [4, 5, 6, 7]}
        }
        self.enemyAnimation = Animator.LoadAnimation(sprites, EnemyAnimationStates.walkingLeft, animation, self.GetAnimationState)
        
        # initializing the parent classes stuff
        super().__init__(self.enemyAnimation.GetCurrentSprite(), position, [0, 0], light=light, collision=True)
        
        # initializing the parameters for the enemy
        self.damage = damage
        self.speed = speed
        self.health = health
        self.sparkRange = sparkRange
        
        self.drops = drops
        self.weapon = weapon
        self.engagementDst = engagementDst**2

        self.weapon.lastFired = time.time() - 0.1  # so they don't instantly fire upon spawning

    # gets the current animation state
    def GetAnimationState(self, *args) -> int:
        if self.velocity[0] > 0: return EnemyAnimationStates.walkingRight
        return EnemyAnimationStates.walkingLeft

    # updates the mob
    def Update(self, events: Events.Manager, dt: float) -> None:
        super().Update(events, dt)

        self.enemyAnimation.Update(events, dt)
        dif = [player.position[0] - self.position[0], player.position[1] - self.position[1]]
        length = math.sqrt(dif[0]**2 + dif[1]**2)
        newVelocity = [dif[0]/length*self.speed, dif[1]/length*self.speed]
        self.velocity = [self.velocity[0]*0.8 + newVelocity[0]*0.2, self.velocity[1]*0.8 + newVelocity[1]*0.2]

        # checking if the mob has a weapon
        if self.weapon:
            # now checking line of sight
            travel = (player.position[0] - self.position[0], player.position[1] - self.position[1])
            travelLength = travel[0]**2 + travel[1]**2  # using the magnitude with everything being squared to reduce square root operations
            if travelLength < self.engagementDst:  # the engagement distance (may need to be fine tuned)
                # checking if the weapon should be fired
                if time.time() - self.weapon.lastFired > abs(self.weapon.fireRate) and random.uniform(0, 1) < dt:
                    for i in range(10):
                        pos = [self.position[0] + travel[0]*i*0.1, self.position[1] + travel[1]*i*0.1]
                        if TileMapCollision(pos): return
                        for obj in solidObjects:  # add tile collision here
                            if obj.CheckCollision(pos): return  # ending the search if there is a block in the way

                    projectiles = self.weapon.ForceFire(travel, self)
                    player.projectiles += projectiles
                    self.weapon.lastFired = time.time()
            else:
                self.weapon.lastFired = time.time() - max(abs(self.weapon.fireRate) - 0.25, 0.1)  # resetting the cooldown so that the mob doesn't instantly shoot upon seeing the player
        # don't put code after here (the method may exit after the weapon firing script)

    # called on kill of the mob
    def Kill(self) -> None:
        # dropping items
        DropLoot(self.drops, self.position)

    # renders the mob
    def Render(self, screen: pygame.Surface, lightMap: pygame.Surface) -> None:
        self.sprite = self.enemyAnimation.GetCurrentSprite()
        super().Render(screen, lightMap)

        # checking for muzzel flash if the mob has a weapon
        if self.weapon:
            if time.time() - self.weapon.lastFired < 0.1:  # mobs don't reload so ignoring that
                if self.enemyAnimation.state == EnemyAnimationStates.walkingLeft:
                    muzzleFlash.Render(lightMap, [round(self.position[0]), round(self.position[1] + self.spriteSize[1]//2)])
                else:
                    muzzleFlash.Render(lightMap, [round(self.position[0] + self.spriteSize[0]), round(self.position[1] + self.spriteSize[1]//2)])


# a particle class
class Particle (Entity):
    def __init__(self, sprite: pygame.Surface, position: list, velocity: list, maxLife: float, light: object=None, name: str="", collision: bool=False) -> None:
        # initializing the parent classes stuff
        super().__init__(sprite, position, velocity, light=light, collision=collision)
        self.lifeTime = time.time()  # when the particle was created (used for destroying it)
        self.maxLife = maxLife
        self.name = name


# for dropped items
class DroppedItem (Particle):
    def __init__(self, sprite: pygame.Surface, position: list, velocity: list, dropType, dropName, amount: int=1) -> None:
        super().__init__(sprite, position, velocity, maxLife=60*8, collision=True)  # initializing the partent classes stuff

        self.amount = amount
        self.dropType = dropType
        self.dropName = dropName

    # adding picking up to the update method
    def Update(self, events: Events.Manager, dt: float, collidables: list=[]) -> None:
        super().Update(events, dt, collidables)

        self.velocity = [self.velocity[0] * 0.9, self.velocity[1] * 0.9]

        # checking for collision with the player
        if player.CheckCollision(self.position):
            self.maxLife = 0  # killing the item

            # giving the item to the player
            if self.dropType == DropTypes.Amo:
                player.amoInventory[self.dropName] += self.amount
            elif self.dropType == DropTypes.Part:
                player.AddPart(self.dropName, self.amount)
                #player.partInventory[self.dropName] += self.amount
            elif self.dropType == DropTypes.Weapon:
                for i in range(self.amount): player.weaponInventory.append(playerWeapons[self.dropName].Copy())
            elif self.outputType == DropTypes.Armor:
                player.AddArmor(self.outputName)
                #player.armorInventory.append(playerArmors[self.outputName])


# a bullet class
class Bullet (Particle):
    def __init__(self, position: list, velocity: list, damage: float, maxLife: float, firer: int, knockback: float) -> None:
        # initializing the parent classes stuff
        #super().__init__(bulletSprite, position, velocity, maxLife, light=bulletLight, name="bullet")
        # without bullet lights
        super().__init__(pygame.transform.scale(bulletSprite, (12, 12)), position, velocity, maxLife, light=None, name="bullet")
        self.collided = False
        self.damage = damage
        self.firer = firer
        self.knockback = knockback
    
    # updates the bullet
    def Update(self, events: Events.Manager, dt: float) -> None:
        # updating the bullet
        positionBefore = self.position[::]
        super().Update(events, dt)

        # getting the dif in position
        subSteps = 20
        dif = [(self.position[0]-positionBefore[0]) / subSteps, (self.position[1]-positionBefore[1]) / subSteps]

        # checking collision along mutliple steps (for more precision)
        if self.firer != Friendlies.enemy:
            for step in range(subSteps):
                pos = [positionBefore[0] + dif[0]*step, positionBefore[1] + dif[1]*step]
                for enemy in mobs:
                    if enemy.CheckCollision(pos):
                        self.collided = True
                        enemy.health -= self.damage
                        
                        # adding knockback from being hit
                        velocityLength = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
                        normalized = [self.velocity[0]/velocityLength, self.velocity[1]/velocityLength]
                        enemy.velocity = [normalized[0] * self.knockback, normalized[1] * self.knockback]
                        
                        return  # ending the loops
        if self.firer != Friendlies.friendly:
            for step in range(subSteps):
                pos = [positionBefore[0] + dif[0]*step, positionBefore[1] + dif[1]*step]
                if player.CheckCollision(pos):
                    self.collided = True
                    player.Damage(self.damage)

                    # adding knockback from being hit
                    velocityLength = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
                    normalized = [self.velocity[0]/velocityLength, self.velocity[1]/velocityLength]
                    player.velocity = [player.velocity[0] - normalized[0] * self.knockback, player.velocity[1] - normalized[1] * self.knockback]

                    return  # ending the loops
    
    # runs when the bullet hits something and is killed
    def Kill(self) -> None:
        gridPosition = tileMap.GetGridPosition(self.position)
        tile = tileMap.GetTileNumber(gridPosition)
        if tile == 9:  # checking if the bullet hit a wooden barrel
            # breaking the barrel
            tileMap.map[gridPosition[1]][gridPosition[0]] = 0
            tileMap.map[gridPosition[1]+1][gridPosition[0]] = 30

            # dropping loot
            DropLoot(woodenBarrelDrops, self.position)
        elif tile == 29:  # checking for an amo crate
            # opening the amo crate
            tileMap.map[gridPosition[1]][gridPosition[0]] = 39

            # dropping loot
            DropLoot(amoCrateDrops, [gridPosition[0]*64+32, gridPosition[1]*64+88])


# a particle for when enimies die
class SparksParticle (Particle):
    def __init__(self, position: list, velocity: list, maxLife: float, value: float=1) -> None:
        super().__init__(sparkSprite, position, velocity, maxLife, light=sparkLight, name="spark", collision=True)
        
        self.value = value
    
    # updating the particle
    def Update(self, events: Events.Manager, dt: float) -> None:
        # moving the particle
        super().Update(events, dt)
        self.velocity = [self.velocity[0]*0.95, self.velocity[1]*0.95]

        # moving the particle to the corner of the screen when it's about to die
        screenPos = [self.position[0] - cameraPos[0] + screenSize[0]//2, self.position[1] - cameraPos[1] + screenSize[1]//2]
        if self.maxLife - (time.time() - self.lifeTime) < 2:
            # checking if the particle is on screen and should be moved
            if screenPos[0] >= 0 and screenPos[0] <= screenSize[0] and screenPos[1] >= 0 and screenPos[1] <= screenSize[1]:
                length = math.sqrt(screenPos[0]**2 + screenPos[1]**2)
                self.velocity = [
                    Mix(self.velocity[0], -screenPos[0]/length*850, dt * 30),
                    Mix(self.velocity[1], -screenPos[1]/length*850, dt * 30)
                ]
                self.collision = False  # turning off collision so it can phase through objects
            else:
                self.maxLife = 0  # killing the particle
                player.exp += self.value  # increasing the players exp count
                player.lastDashed -= self.value * 0.25  # making the dash cooldown go quicker to reward quick flowier fighting hopefully to better allow that style of playing
                player.health = min(player.health + self.value * 0.5, 100)


# =============================================================================
#                               Player
#=============================================================================


# cashes a render of an item slot (to improve preformance since drawing text is super slow)
class ItemSlot:
    def __init__(self, sprite: pygame.Surface, name: str, itemType: DropTypes, amount: int) -> None:
        self.sprite = sprite
        self.name = name
        self.itemType = itemType
        self.amount = amount
        self.surface = pygame.Surface((56, 56))  # (self.sprite.get_size())
        
        self.highlighted = False  # for when an item is selected or equiped
        
        # generating an initial cash for the slot
        self.UpdateCash(self.amount)
    
    # checks for a collision with the box
    def CheckCollision(self, boxPosition: tuple, mousePosition: tuple):
        relativePos = [mousePosition[0] - boxPosition[0], mousePosition[1] - boxPosition[1]]
        return (relativePos[0] > 0 and relativePos[0] < 56) and (relativePos[1] > 0 and relativePos[1] < 56)

    # creates a new cashed render
    def UpdateCash(self, newAmount: int) -> None:
        self.amount = newAmount  # updating the number field
        
        # clearing the surface
        self.surface.fill((1, 1, 1))
        self.surface.set_colorkey((1, 1, 1))

        # getting the color
        color = uiColorPallete.color
        if self.highlighted:
            # highlighting the slot (this is done when it's selected)
            color = (color[0] * 1.35, color[1] * 1.35, color[2] * 1.35)

        # rendering a new slot
        pygame.draw.rect(self.surface, color, [2, 2, 52, 52], 0, 0)
        pygame.draw.rect(self.surface, uiColorPallete.brightColor, [0, 0, 56, 56], 2, 2)
        self.surface.blit(self.sprite, [4, 4])
        UI.DrawText(self.surface, 15, "pixel2.ttf", f"{self.amount}", (5, 37), uiColorPallete.textColor)
    
    # renders the surface
    def Render(self, screen: pygame.Surface, position: tuple) -> None:
        screen.blit(self.surface, position)


# stores a crafting recipe
class CraftingRecipe:
    def __init__(self, ingredients: list, outputType: DropTypes, outputName: any, amount: int, sprite: pygame.Surface) -> None:
        self.ingredients = ingredients
        self.outputType = outputType
        self.outputName = outputName
        self.amount = amount
        self.sprite = sprite

        # pre generate the crafting inventory tile
        self.surface = pygame.Surface((56, 56))
        self.CashRender()
    
    # checks for a collision with the box
    def CheckCollision(self, boxPosition: tuple, mousePosition: tuple):
        relativePos = [mousePosition[0] - boxPosition[0], mousePosition[1] - boxPosition[1]]
        return (relativePos[0] > 0 and relativePos[0] < 56) and (relativePos[1] > 0 and relativePos[1] < 56)

    # chases the render for the item slot
    def CashRender(self) -> None:
        # clearing the surface
        self.surface.fill((1, 1, 1))
        self.surface.set_colorkey((1, 1, 1))

        # rendering a new slot
        pygame.draw.rect(self.surface, uiColorPallete.color, [2, 2, 52, 52], 0, 0)
        pygame.draw.rect(self.surface, uiColorPallete.brightColor, [0, 0, 56, 56], 2, 2)
        self.surface.blit(self.sprite, [4, 4])
        UI.DrawText(self.surface, 15, "pixel2.ttf", f"{self.amount}", (5, 37), uiColorPallete.textColor)

    # checks for ingredients
    def CheckIngredients(self, player: object) -> bool:
        # checking that the player has enough of every ingredient
        for ingredient, amount in self.ingredients:
            if player.partInventory[ingredient] < amount: return False
        return True
    
    # crafts the item
    def Craft(self, player: object) -> None:
        # removing the ingredients from the player
        for ingredient, amount in self.ingredients:
            player.RemovePart(ingredient, amount)
        
        # adding the crafted item
        if self.outputType == DropTypes.Amo:
            player.amoInventory[self.outputName] += self.amount
        elif self.outputType == DropTypes.Part:
            player.AddPart(self.outputName, self.amount)
        elif self.outputType == DropTypes.Weapon:
            for i in range(self.amount): player.weaponInventory.append(playerWeapons[self.outputName].Copy())
        elif self.outputType == DropTypes.Armor:
            player.AddArmor(self.outputName)
            #player.armorInventory.append(playerArmors[self.outputName])


# the player entity
class Player (Entity):
    def __init__(self, sprites: pygame.Surface, light: object) -> None:
        # creating the animation for the player
        animation = {
            PlayerStates.walkingRight: {"speed": 8, "reset": False, "sprites": [0, 1, 2, 3]},
            PlayerStates.walkingLeft: {"speed": 8, "reset": False, "sprites": [4, 5, 6, 7]},
            PlayerStates.idle: {"speed": 2, "reset": True, "sprites": [12, 13]}
        }
        self.playerAnimation = Animator.LoadAnimation(sprites, PlayerStates.walkingLeft, animation, self.GetAnimationState)
        self.lastAnimationState = PlayerStates.walkingRight
        
        # initializing the parent classes stuff
        super().__init__(self.playerAnimation.GetCurrentSprite(), [64*25//2, 64*25//2 - 128], [0, 0], light=light, collision=True)

        # stats about the player
        self.stats = {
            "dashCooldown": 5.5,
            "speed": 100,
            "reach": 100**2,  # idk if this will be a changeable stat, the squaring is so magnitudes can be compared instead of distances to save a square root operation
        }
        
        # movement stuff
        self.dash = 1
        self.lastDashed = 0

        # health and damage stuff
        self.health = 100
        self.lastDamaged = 0

        # the projectiles the player has shot
        self.projectiles = []
        self.deadProjectiles = []

        self.exp = 0

        self.weaponSlot = 0
        self.weaponInventory = [playerWeapons["Pipe Pistol"].Copy()]#[playerWeapons["Pipe Pistol"], playerWeapons["Pipe Shotty"], playerWeapons["SAR"]]
        self.amoInventory = {
            AmoType.Pistol: 35,
            AmoType.LargeRifle: 11,
            AmoType.Shotgun: 42,
            AmoType.Rifle: 125
        }

        # all the armor the player has in their inventory
        self.armorInventory = []
        self.selectedArmor = -1

        # all the parts the player has
        self.partInventory = {
            "Rusty Pipe": 0,
            "Scrap Metal": 0,
            "Rusty Nails": 0,
            "Wire Spool": 0,
            "Wood": 0,
            "Gunpowder": 0,
            "Metal Pipe": 0,
            "Metal Sheet": 0,
            "Nails": 0,
            "Brass Casings": 0,
            "Jerry Can": 0,
            "Oil Can": 0,
            "Fire Powder": 0,
            "Spring": 0
        }
        self.inventorySlots = []  # for all the cashed slots (cashed for preformance)
        self.openInventory = False
        self.selectedRecipe = -1  # the recipe currently selected

        self.inCraftingBenchT1 = False
        self.leftPadding = 0  # padding for the position of the players inventory
        self.rightPadding = 0  # padding for the position of the players inventory
        self.craftButton = UI.Button((235, 235), (80, 30), uiColorPallete, "Craft", textSize=20, font="pixel2.ttf", transparentColor=(254, 254, 254))
        self.craftIngredientCash = pygame.Surface((265, 215))
        self.craftIngredientCash.set_colorkey((0, 0, 0))

    # adds a new piece of armor to the players inventory
    def AddArmor(self, name: str) -> None:
        # finding if the player already has it in their inventory
        for armor in self.armorInventory:
            if armor.name == name:
                armor.UpdateCash(armor.amount + 1)
                return  # ending early so it doesn't dupe a new copy
        
        self.armorInventory.append(ItemSlot(playerArmors[name].itemSprite, name, DropTypes.Armor, 1))  # adding a new item for it

    # adds a new part
    def AddPart(self, partName: str, amount: int) -> None:
        if self.partInventory[partName]:  # adding to an already existing part
            self.partInventory[partName] += amount
            for slot in self.inventorySlots:
                if slot.name == partName: slot.UpdateCash(self.partInventory[partName])
        else:  # adding a new slot for a new item
            self.partInventory[partName] = amount
            self.inventorySlots.append(ItemSlot(partDropSpritesDoubleScale[partNames.index(partName)], partName, DropTypes.Part, amount))
    
    # removes a part
    def RemovePart(self, partName: str, amount: int) -> None:
        self.partInventory[partName] -= amount
        if self.partInventory[partName]:  # updating the cash
            for slot in self.inventorySlots:
                if slot.name == partName: slot.UpdateCash(self.partInventory[partName])
        else:  # removing the slot as nothing is left
            valid = []
            for slot in self.inventorySlots:
                if slot.name != partName: valid.append(slot)
            self.inventorySlots = valid

    # renders the ui (mainly the inventory)
    def RenderUI(self, screen: pygame.Surface) -> None:
        if self.openInventory:
            # cell is 24x24 2 padding each side, 2 wide boarder, 5 separation
            width = screenSize[0] - 120 - self.leftPadding - self.rightPadding  # 60 padding on each side
            cellSize = 24*2 + 2+2 + 2+2 + 5  # 56 i think
            cells = width // cellSize

            # rendering the inventory
            i = 0
            for slot in self.inventorySlots+self.armorInventory:
                x = (i%cells) * cellSize + 60 + self.leftPadding
                y = (i//cells) * cellSize + 60
                slot.Render(screen, [x, y])
                i += 1
            
            # rendering the crafting menu
            if self.inCraftingBenchT1:
                i = 0
                numCells = 4#265//cellSize#240 // cellSize
                offset = (265 - numCells*cellSize)*0.5
                for recipe in craftingRecipesTier1:
                    # rendering the item slot
                    x = (i%numCells) * cellSize + 60 + offset
                    y = (i//numCells) * cellSize + 60+250
                    screen.blit(recipe.surface, (x, y))
                    i += 1
                
                # rendering the recipe window
                pygame.draw.rect(screen, uiColorPallete.color, [62, 62, 261, 211])
                pygame.draw.rect(screen, uiColorPallete.brightColor, [60, 60, 265, 215], 2, 4)  # 25 less padding on inventory side than screen edge

                # rendering the selected recipe
                if self.selectedRecipe >= 0:
                    # drawing the ingredients
                    i = 0

                    screen.blit(self.craftIngredientCash, (65, 65))
                    # cash this render
                    #for ingredient, amount in craftingRecipesTier1[self.selectedRecipe].ingredients:
                    #    UI.DrawText(screen, 20, "pixel2.ttf", f"{amount}x {ingredient}", (65, 65 + i*25), uiColorPallete.textColor)
                    #    i += 1
                    
                    # rendering the craft button
                    self.craftButton.Render(screen, events)  # idk how to move the update sequence to another section because of how it was made and also I don't want to be redundently checking the able to craft the recipe
                    
                    # checking if the player is trying to craft
                    validRecipe = craftingRecipesTier1[self.selectedRecipe].CheckIngredients(self)
                    if not validRecipe:
                        if self.craftButton.state not in [UI.Button.States.held, UI.Button.States.realeased]:
                            # resetting the cashed render
                            self.craftButton.state = UI.Button.States.held
                            self.craftButton.forceUpdate = True
                            self.craftButton.textRenderer.size = self.craftButton.textSize - 3
                        else: self.craftButton.state = UI.Button.States.held  # forcing it to stay as held
                    elif self.craftButton.state == UI.Button.States.pressed and events.mouseStates["left"] == Events.MouseStates.pressed:
                        # crafting the recipe the player selected
                        craftingRecipesTier1[self.selectedRecipe].Craft(self)
    
    # gets the current animation state of the player
    def GetAnimationState(self, events: Events.Manager, dt: float) -> PlayerStates:
        if ord("d") in events.held or pygame.K_RIGHT in events.held:
            self.lastAnimationState = PlayerStates.walkingRight
            return PlayerStates.walkingRight
        if ord("a") in events.held or pygame.K_LEFT in events.held:
            self.lastAnimationState = PlayerStates.walkingLeft
            return PlayerStates.walkingLeft
        if ord("w") in events.held or pygame.K_UP in events.held:    return self.lastAnimationState
        if ord("s") in events.held or pygame.K_DOWN in events.held:  return self.lastAnimationState
        
        return PlayerStates.idle
        #if self.lastAnimationState == PlayerStates.walkingLeft: return PlayerStates.idleLeft
        #return PlayerStates.idleRight

    # damages the player
    def Damage(self, damage: int) -> None:
        # checking for armor
        finalDamage = damage
        if self.selectedArmor != -1:  # checking if the player is wearing armor
            finalDamage = round(playerArmors[self.armorInventory[self.selectedArmor].name].ReduceDamage(damage), 0)
        
        # damaging the player
        self.health = max(self.health - finalDamage, 0)
        if self.health <= 0:
            pass  # kill the player
    
    # updating the player
    def Update(self, events: Events.Manager, dt: float) -> None:
        # dashing
        timeSinceDash = time.time() - self.lastDashed
        if pygame.K_SPACE in events.events and timeSinceDash > self.stats["dashCooldown"]:
            self.dash = 5
            self.lastDashed = time.time()
        elif timeSinceDash > 0.2:
            self.dash = Mix(self.dash, 1, dt*5)
        
        # moving the player based on keyboard input
        inputed = [False, False]
        inputs = {
            "up": ord("w") in events.held or pygame.K_UP in events.held,
            "down": ord("s") in events.held or pygame.K_DOWN in events.held,
            "left": ord("a") in events.held or pygame.K_LEFT in events.held,
            "right": ord("d") in events.held or pygame.K_RIGHT in events.held
        }
        if inputs["up"] and not inputs["down"]:
            inputed[1] = True
            self.velocity[1] = Mix(self.velocity[1], -self.stats["speed"]*self.dash, dt*15)
        if inputs["down"] and not inputs["up"]:
            inputed[1] = True
            self.velocity[1] = Mix(self.velocity[1], self.stats["speed"]*self.dash, dt*15)
        if inputs["left"] and not inputs["right"]:
            inputed[0] = True
            self.velocity[0] = Mix(self.velocity[0], -self.stats["speed"]*self.dash, dt*15)
        if inputs["right"] and not inputs["left"]:
            inputed[0] = True
            self.velocity[0] = Mix(self.velocity[0], self.stats["speed"]*self.dash, dt*15)
        
        # checking if the held weapon switched
        for i in range(1, 9):
            if str(i) in events.typed:
                if i <= len(self.weaponInventory):
                    self.weaponSlot = i - 1
                break
        
        # adding drag once the player stops moving
        if not inputed[0]: self.velocity[0] = Mix(self.velocity[0], 0, dt*10)
        if not inputed[1]: self.velocity[1] = Mix(self.velocity[1], 0, dt*10)

        weapon = self.weaponInventory[self.weaponSlot]
        validToFire = True  # if it's valid to fire on this frame

        # checking if the player is in a crafting menu
        if self.inCraftingBenchT1:
            # checking if the player has moved away from the crafting bench
            dif = [player.position[0]-self.inCraftingBenchT1[0], player.position[1]-self.inCraftingBenchT1[1]]
            dst = dif[0]**2 + dif[1]**2
            if dst > self.stats["reach"]: self.inCraftingBenchT1 = False  # closing the menu

            # checking if the player has selected a recipe
            if events.mouseStates["left"] == Events.MouseStates.pressed:
                i = 0
                cellSize = 24*2 + 2+2 + 2+2 + 5  # 56 i think
                numCells = 4#265//cellSize#240 // cellSize
                offset = (265 - numCells*cellSize)*0.5
                for recipe in craftingRecipesTier1:
                    x = (i%numCells) * cellSize + 60 + offset
                    y = (i//numCells) * cellSize + 60+250
                    screen.blit(recipe.surface, (x, y))
                    if recipe.CheckCollision((x, y), events.mousePos):
                        # selecting the recipe
                        self.selectedRecipe = i
                        
                        # creating the new cash
                        j = 0
                        self.craftIngredientCash = pygame.Surface((265, 215))
                        self.craftIngredientCash.set_colorkey((0, 0, 0))
                        for ingredient, amount in craftingRecipesTier1[self.selectedRecipe].ingredients:
                            UI.DrawText(self.craftIngredientCash, 20, "pixel2.ttf", f"{amount}x {ingredient}", (0, j*25), uiColorPallete.textColor)
                            j += 1

                        validToFire = False  # the player shouldn't shoot when messing with the menu
                        break
                    i += 1
                
                # checking if the player was clicking the crafting window (to stop the gun from firing)
                if (events.mousePos[0] > 60 and events.mousePos[0] < 325) and (events.mousePos[1] > 60 and events.mousePos[1] < 275): validToFire = False
        else:  # making sure the padding for the crafting menu is reset if it's not actively open
            self.leftPadding = 0
        
        # checking if the player click on a cell in the inventory to stop it from firing and also to interact with it
        if self.openInventory:
            if events.mouseStates["left"] == Events.MouseStates.pressed:
                width = screenSize[0] - 120 - self.leftPadding - self.rightPadding  # 60 padding on each side
                cellSize = 24*2 + 2+2 + 2+2 + 5  # 56 i think
                cells = width // cellSize

                # rendering the inventory
                i = 0
                for slot in self.inventorySlots+self.armorInventory:
                    x = (i%cells) * cellSize + 60 + self.leftPadding
                    y = (i//cells) * cellSize + 60
                    clicked = slot.CheckCollision((x, y), events.mousePos)
                    if clicked:  # checking if the box was clicked
                        validToFire = False
                        if slot.itemType == DropTypes.Armor:  # selecting the armor and deselecting any previously selected ones
                            if self.selectedArmor > -1:
                                # resetting the old selected one
                                oldSlot = self.armorInventory[self.selectedArmor]
                                oldSlot.highlighted = False
                                oldSlot.UpdateCash(oldSlot.amount)
                            
                            # selecting the new one
                            self.selectedArmor = self.armorInventory.index(slot)
                            slot.highlighted = True
                            slot.UpdateCash(slot.amount)
                        break
                    i += 1

        # checking if the weapon should fire
        if validToFire and weapon.ValidFire(events, dt):
            # firing the weapon
            self.projectiles += weapon.Fire(self)

        # reloading the weapon
        if ord("r") in events.held and weapon.capacityLeft < weapon.capacity and not weapon.reloading:
            weapon.Reload()
        
        # opening the inventory
        if pygame.K_TAB in events.events:
            self.openInventory = not self.openInventory
            self.inCraftingBenchT1 = False
        
        # closing different menus
        if pygame.K_ESCAPE in events.held:
            self.openInventory = False
            self.inCraftingBenchT1 = False
        
        # checking if the player is trying to interact with an object
        if events.mouseStates["right"] == Events.MouseStates.pressed:
            # making sure the object is in range
            mapMousePos = [cameraPos[0] - screenSize[0]//2 + events.mousePos[0], cameraPos[1] - screenSize[1]//2 + events.mousePos[1]]
            dif = [mapMousePos[0] - player.position[0], mapMousePos[1] - player.position[1]]
            dst = dif[0]**2 + dif[1]**2
            if dst <= self.stats["reach"]:
                # checking what the player is clicking
                tileMousePos = tileMap.GetGridPosition(mapMousePos)
                mouseTile = tileMap.GetTileNumber(tileMousePos)
                if not self.inCraftingBenchT1 and mouseTile in tier1CraftingTiles:
                    self.inCraftingBenchT1 = [self.position[0], self.position[1]]
                    self.openInventory = True
                    self.leftPadding = 300  # the width of the crafting tab
                    self.selectedRecipe = -1  # no recipe is selected when you first open the menu

                    # clearing the cash
                    self.craftIngredientCash = pygame.Surface((265, 215))
                    self.craftIngredientCash.set_colorkey((0, 0, 0))

        # updating the parent class (does most of the moving)
        super().Update(events, dt)
        
        # updating the projectiles
        aliveProjectiles = []
        for projectile in self.projectiles:
            projectile.Update(events, dt)

            # checking if the projectile is still alive
            alive = time.time() - projectile.lifeTime < projectile.maxLife
            alive = alive and ((projectile.name == "bullet" and not projectile.collided) or projectile.name != "bullet")
            if (projectile.name != "spark" or projectile.collision):
                for obj in solidObjects:  # add tile collision here
                    alive = alive and not obj.CheckCollision(projectile.position)
                alive = alive and not TileMapCollision(projectile.position)
            if alive:
                aliveProjectiles.append(projectile)
            else:
                projectile.Kill()
        
        # updating the projectiles
        self.projectiles = aliveProjectiles

        # updating the animation controller
        self.playerAnimation.Update(events, dt)

    # rendering the player
    def Render(self, screen: pygame.Surface, lightMap: pygame.Surface) -> None:
        # updating the sprite
        self.sprite = self.playerAnimation.GetCurrentSprite()

        # rendering the projectiles
        for projectile in self.projectiles:
            projectile.Render(screen, lightMap)
        
        # rendering the stuff in the parent class
        super().Render(screen, lightMap, (0, 16))

        # rendering the weapon
        weapon = self.weaponInventory[self.weaponSlot]
        allWeapons = [key for key in playerWeapons]
        weaponIndex = allWeapons.index(weapon.name)
        yOffset = 0
        xOffset = 0
        if self.playerAnimation.state == PlayerStates.walkingLeft:
            weaponIndex += len(allWeapons)
            if int(self.playerAnimation.frame % 2) == 1: xOffset = 4
        elif self.playerAnimation.state == PlayerStates.idle and int(self.playerAnimation.frame % 2) == 1: yOffset = 4
        elif int(self.playerAnimation.frame % 2) == 1: xOffset = -4
        renderPos = [self.position[0] - self.spriteSize[0]//2 - cameraPos[0] + screenSize[0]//2 - xOffset, self.position[1] - self.spriteSize[1]//2 - cameraPos[1] + screenSize[1]//2 + yOffset]
        screen.blit(weaponSprites[weaponIndex], renderPos)

        # rendering muzzel flash
        lastFired = weapon.lastFired
        if weapon.reloading: lastFired = weapon.lastFired + abs(weapon.fireRate) - weapon.reloadSpeed
        if weapon.fired and time.time() - lastFired < 0.05:  # min(abs(self.weapon.fireRate)-0.005, 0.05):
            if self.playerAnimation.state == PlayerStates.walkingLeft:
                muzzleFlash.Render(lightMap, [round(self.position[0]), round(self.position[1] + self.spriteSize[1]//2)])
            else:
                muzzleFlash.Render(lightMap, [round(self.position[0] + self.spriteSize[0]), round(self.position[1] + self.spriteSize[1]//2)])

        # rendering the weapon cooldown
        cooldown = min((time.time() - weapon.lastFired) / abs(weapon.fireRate), 1)
        if weapon.reloading:
            cooldown = min((time.time() - lastFired) / abs(weapon.reloadSpeed), 1)
        translatedPosition = [self.position[0] - cameraPos[0] + screenSize[0]//2, self.position[1] - cameraPos[1] + screenSize[1]//2]
        pygame.draw.rect(screen, [255, 255, 0], [translatedPosition[0] - 17, translatedPosition[1] + 35, 35, 14])
        pygame.draw.rect(screen, [225, 225, 225], [translatedPosition[0] - 15, translatedPosition[1] + 37, 30, 10])
        pygame.draw.rect(screen, [75, 75, 75], [translatedPosition[0] - 15, translatedPosition[1] + 37, 30*(1-cooldown), 10])


# a armor class
class Armor:
    def __init__(self, name: str, itemSprite: pygame.Surface, protection: float) -> None:
        self.name = name
        self.itemSprite = itemSprite
        self.protection = protection  # a percentage of how much damage will be removed
    
    # adjusts a damage value for the protection of the armor
    def ReduceDamage(self, damage: float) -> float:
        return damage - damage*self.protection


# a weapons class
class Weapon:
    def __init__(self, name: str, fireRate: float, speed: float, damage: float, projectileObject: object, capacity: float, reloadSpeed: float, firer: int, amoType: int, capacityLeft: float=-1, maxLife: float=0.5, accuracy: float=0, selfKnockback: float = 0, knockback: float=200, burst: int=1) -> None:
        self.fireRate = fireRate  # negative == semi auto
        self.speed = speed
        self.damage = damage
        self.projectileObject = projectileObject
        self.lastFired = 0
        self.name = name
        self.maxLife = maxLife
        self.accuracy = accuracy
        self.selfKnockback = selfKnockback
        self.burst = burst
        self.knockback = knockback
        self.fired = False

        self.reloading = False
        self.capacity = capacity
        self.reloadSpeed = reloadSpeed
        self.capacityLeft = capacityLeft
        if self.capacityLeft == -1: self.capacityLeft = self.capacity

        self.amoType = amoType
        self.firer = firer
    
    # copies the object
    def Copy(self) -> object:
        return Weapon(self.name, self.fireRate, self.speed, self.damage, self.projectileObject, self.capacity, self.reloadSpeed, self.firer, self.amoType, capacityLeft=self.capacityLeft, maxLife=self.maxLife, accuracy=self.accuracy, selfKnockback=self.selfKnockback, knockback=self.knockback, burst=self.burst)

    # checks if it is valid to fire
    def ValidFire(self, events: Events.Manager, dt: float) -> bool:
        # checking if the time since the last fired shot is long enough
        if (time.time() - self.lastFired < abs(self.fireRate)): return False
        
        # checking if the gun and player are out of amo
        if not player.amoInventory[self.amoType] and not self.capacityLeft: return False

        # checking if the gun finished reloading (in the case it was)
        self.fired = False
        if self.reloading:
            self.reloading = False
            if player.amoInventory[self.amoType] >= self.capacity - self.capacityLeft:
                player.amoInventory[self.amoType] -= self.capacity - self.capacityLeft
                self.capacityLeft = self.capacity
            else:
                self.capacityLeft += player.amoInventory[self.amoType]
                player.amoInventory[self.amoType] = 0

        # making sure there is amo left
        if not self.capacityLeft: return False

        # checking if the weapon was clicked
        if events.mouseStates["left"] == Events.MouseStates.held and self.fireRate > 0:
            return True
        elif events.mouseStates["left"] == Events.MouseStates.pressed and self.fireRate < 0:
            return True
        
        # no valid option for firing was found
        return False
    
    # reloads the weapon
    def Reload(self) -> None:
        #self.capacityLeft = self.capacity
        if not player.amoInventory[self.amoType]: return
        self.lastFired = time.time() + self.reloadSpeed - abs(self.fireRate)
        self.reloading = True
        self.fired = False

    # force fires the weapon
    def ForceFire(self, direction: list, entity: Entity) -> list:  # mainly used for mobs so that it doesn't mess with the player (it won't cause a reload and ignors all amo counts)
        projectiles = []

        # firing the weapon
        for i in range(self.burst):
            self.fired = True
            # creating a projectile
            dif = direction
            length = math.sqrt(dif[0]*dif[0] + dif[1]*dif[1])
            dif = [dif[0] / length + random.uniform(-self.accuracy, self.accuracy), dif[1] / length + random.uniform(-self.accuracy, self.accuracy)]
            length = math.sqrt(dif[0]*dif[0] + dif[1]*dif[1])
            normalized = [dif[0] / length, dif[1] / length]
            velocity = [normalized[0] * 10, normalized[1] * 10]
            projectile = self.projectileObject([entity.position[0] + velocity[0], entity.position[1] + velocity[1]], [velocity[0] * self.speed, velocity[1] * self.speed], self.damage, self.maxLife, self.firer, self.knockback)
            projectiles.append(projectile)

            # knockback
            entity.velocity = [entity.velocity[0] - normalized[0] * self.selfKnockback, entity.velocity[1] - normalized[1] * self.selfKnockback]
        
        return projectiles

    # updates the weapon
    def Fire(self, player: object) -> list:
        # updating the time at which it was last fired
        self.lastFired = time.time()
        projectiles = []

        self.capacityLeft -= 1
        
        for i in range(self.burst):
            self.fired = True
            # creating a projectile
            dif = [events.mousePos[0] - (player.position[0] - cameraPos[0] + screenSize[0]//2), events.mousePos[1] - (player.position[1] - cameraPos[1] + screenSize[1]//2)]
            length = math.sqrt(dif[0]*dif[0] + dif[1]*dif[1])
            dif = [dif[0] / length + random.uniform(-self.accuracy, self.accuracy), dif[1] / length + random.uniform(-self.accuracy, self.accuracy)]
            length = math.sqrt(dif[0]*dif[0] + dif[1]*dif[1])
            normalized = [dif[0] / length, dif[1] / length]
            velocity = [normalized[0] * 10, normalized[1] * 10]
            projectile = self.projectileObject([player.position[0] + velocity[0], player.position[1] + velocity[1]], [velocity[0] * self.speed, velocity[1] * self.speed], self.damage, self.maxLife, self.firer, self.knockback)
            projectiles.append(projectile)

            # knockback
            player.velocity = [player.velocity[0] - normalized[0] * self.selfKnockback, player.velocity[1] - normalized[1] * self.selfKnockback]

        # reloading if empty
        if not self.capacityLeft and player.amoInventory[self.amoType] and settings["Gameplay"]["Controls"]["auto reload"]:
            #self.capacityLeft = self.capacity
            self.lastFired = time.time() + self.reloadSpeed - abs(self.fireRate)
            self.reloading = True
        
        # returning the projectiles
        return projectiles


# =============================================================================
#                               Functions
#=============================================================================


# drops loot
def DropLoot(drops, position) -> None:
    for drop in drops:
        # drop type, name, amount range, chance (0-10)
        randomChance = random.uniform(0, 10)
        if drop[3] >= randomChance:
            amount = random.randint(drop[2][0], drop[2][1])
            if not amount: continue  # making sure to not create an item with 0 quantity
            
            # generating info for the dropped item
            randomVelocity = [random.uniform(-5, 5), random.uniform(-5, 5)]
            randVelLength = math.sqrt(randomVelocity[0]**2 + randomVelocity[1]**2)
            randLength = random.uniform(75, 250)
            randomVelocity = [randomVelocity[0]/randVelLength*randLength, randomVelocity[1]/randVelLength*randLength]
            
            # creating the dropped item
            if drop[0] == DropTypes.Amo:  # dropping amo                    
                dropSprite = amoSprites[[AmoType.Pistol, AmoType.LargeRifle, AmoType.Shotgun, AmoType.Rifle].index(drop[1])]
                dropped = DroppedItem(dropSprite, position, randomVelocity, drop[0], drop[1], amount=amount)
                player.projectiles.append(dropped)
            elif drop[0] == DropTypes.Part:  # dropping parts
                dropSprite = partDropSprites[partNames.index(drop[1])]
                dropped = DroppedItem(dropSprite, position, randomVelocity, DropTypes.Part, drop[1], amount=amount)
                player.projectiles.append(dropped)


# mixes two values
def Mix(l: any, r: any, v: float) -> float:
    return l * (1 - v) + r * v


# checks for a collision with a block for a given position
def TileMapCollision(pos: tuple) -> bool:
    tile = tileMap.GetTileNumber(tileMap.GetGridPosition(pos))
    if tile in solidTiles:
        # pulling up the hitbox and checking
        #tilePosition = (round(pos[0] // tileMap.tileSize), round(pos[1] // tileMap.tileSize))
        subPosition = (pos[0] % tileMap.tileSize, pos[1] % tileMap.tileSize)
        hitBox = tileHitBoxes[solidTiles.index(tile)]
        return hitBox.Collide(subPosition)
    else: return False


# gets the hitbox if any for a given position
def GetTileMapCollisionHitbox(pos: tuple) -> object:
    tile = tileMap.GetTileNumber(tileMap.GetGridPosition(pos))
    if tile in solidTiles:
        return tileHitBoxes[solidTiles.index(tile)]


# loads a level
def LoadLevel(levelName: str) -> None:
    global tileMap, solidObjects, lights
    solidObjects = []
    lights = []

    # loading the tileMap for the level
    tileMap = TileMap.TileMap(f"{levelName}.txt", tiles, 64)

    # opening the level information json file
    levelFile = json.load(open(f"{levelName}.json"))

    # loading the solid objects
    for obj in levelFile["Objects"]:
        solidObjects.append(ShadowedObject(
            obj["position"],
            obj["size"],
            sprite=tiles[obj["tileNumber"]],
            renderShadows=obj["renderShadows"],
            renderObject=obj["renderSelf"],
            collideable=obj["collideable"]
        ))

    # loading the lights
    for light in levelFile["Lights"]:
        lights.append(Light(
            light["radius"],
            light["color"],
            light["stepSize"],
            light["renderShadows"],
            light["position"]
        ))


# updates the different things effected by the settings
def UpdateSettings() -> None:
    global bulletLight, sparkLight, muzzleFlash
    
    # updating lighting information (mostly about shadows)
    bulletLight = RadialLight(40, (160, 140, 50), 1, settings["render"]["lighting"]["bullet"])  # is currently disabled since the bullet light doesn't match well, although might be used in other weapons, idk
    sparkLight = RadialLight(30, (175/2, 125/2, 0), 1, settings["render"]["lighting"]["sparks"])
    muzzleFlash = RadialLight(375, (225, 75, 25), 1, settings["render"]["lighting"]["muzzleFlash"])

# the settings for variouse things
settings = {
    "render": {
        "lighting": {  # aka shadows
            "bullet": False,  # (lighting for this is currently disabled anyways) doesn't visually really do anything because the lighting is so minimal
            "sparks": False,  # doesn't visually really do anything because the lighting is so minimal
            "muzzleFlash": False
        }
    },
    "Gameplay": {
        "Controls": {
            "auto reload": True
        }
    }
}


# =============================================================================
#                               General Variables
#=============================================================================


# creating some lights
light = RadialLight(240, (225, 225, 225), 1)
bulletLight = RadialLight(40, (160, 140, 50), 1, settings["render"]["lighting"]["bullet"])
sparkLight = RadialLight(30, (175/2, 125/2, 0), 1, settings["render"]["lighting"]["sparks"])
muzzleFlash = RadialLight(375, (225, 75, 25), 1, settings["render"]["lighting"]["muzzleFlash"])

# different color pallets to keep all the colors in sync
uiColorPallete = UI.ColorPalette((34, 32, 52), (98, 94, 128), (203, 219, 252), (255, 255, 255))

# creating a basic tilemap (this will need to be replaced with a function to load and stuff for multiple levels and areas)
img = pygame.image.load("ShooterTiles.png")
tiles = Sprites.ScaleSprites(Sprites.LoadSpritesheet(img, (16, 16)), (64, 64))
#tileMap = TileMap.TileMap("shooterExampleLevel.txt", tiles, 64)
tiles.insert(0, TileMap.blankTile)

solidTiles = [1, 2, 3, 4, 5, 6, 7, 9, 11, 12, 13, 14, 16, 18, 19, 20, 25, 26, 27, 28, 29, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 46, 49, 50, 52, 53, 54, 55, 56, 57, 59, 60, 61, 62, 63, 64, 68, 70, 71, 72, 78, 79, 80, 83, 84, 85, 86, 87, 88, 91, 92, 93, 94, 95, 96]
tileHitBoxes = [
    HitBox((0, 0), (64, 24)),  # 1
    HitBox((0, 32), (64, 32)),  # 2
    HitBox((0, 0), (12, 64)),  # 3
    HitBox((0, 0), (12, 64)),  # 4
    HitBox((52, 0), (12, 64)),  # 5
    HitBox((52, 0), (12, 64)),  # 6
    HitBox((20, 0), (24, 64)),  # 7
    HitBox((8, 52), (48, 12)),  # 9 top of wooden barrel
    HitBox((0, 0), (12, 64)),  # 11
    HitBox((0, 0), (12, 64)),  # 12
    HitBox((52, 0), (12, 64)),  # 13
    HitBox((52, 0), (12, 64)),  # 14
    HitBox((8, 20), (48, 44)),  # 16 top of oil barrel
    HitBox((8, 28), (44, 12)),  # 18 amo crate
    HitBox((0, 0), (64, 24)),  # 19
    HitBox((0, 0), (64, 24)),  # 20
    HitBox((0, 0), (64, 64)),  # 25 top of storage container
    HitBox((0, 0), (64, 64)),  # 26 top of storage container
    HitBox((0, 0), (64, 24)),  # 27
    HitBox((0, 0), (64, 24)),  # 28
    HitBox((8, 28), (44, 12)),  # 29 amo crate w/ block under
    HitBox((8, 20), (48, 44)),  # 32 top of empty oil barrel
    HitBox((0, 0), (64, 64)),  # 33 mid section of storage container
    HitBox((0, 0), (64, 64)),  # 34 mid section of storage container
    HitBox((8, 48), (48, 16)),  # 35 top of lanturn on box
    HitBox((0, 0), (64, 64)),  # 36 top of house
    HitBox((0, 0), (64, 64)),  # 37 top of house
    HitBox((0, 0), (64, 64)),  # 38 top of house
    HitBox((8, 28), (44, 12)),  # 39 opened amo crate
    HitBox((8, 48), (48, 16)),  # 40 top of box
    HitBox((0, 0), (64, 64)),  # 41 top of storage container door
    HitBox((0, 0), (64, 64)),  # 42 top of storage container door
    HitBox((0, 0), (64, 64)),  # 44 top mid of house
    HitBox((0, 0), (64, 64)),  # 45 top mid of house
    HitBox((0, 0), (64, 64)),  # 46 top mid of house
    HitBox((0, 0), (64, 32)),  # 49 bottom of storage container door
    HitBox((0, 0), (64, 32)),  # 50 bottom of storage container door
    HitBox((0, 0), (64, 64)),  # 52 top roof of house
    HitBox((0, 0), (64, 64)),  # 53 top roof of house
    HitBox((0, 0), (64, 64)),  # 54 top roof of house
    HitBox((0, 0), (64, 64)),  # 55 tree top
    HitBox((0, 0), (64, 64)),  # 56 tree top
    HitBox((8, 48), (48, 16)),  # 57 top of water barrel
    HitBox((0, 0), (64, 24)),  # 59 top of metal crate
    HitBox((0, 0), (64, 44)),  # 60 roof of house
    HitBox((0, 0), (64, 44)),  # 61 roof of house
    HitBox((0, 0), (64, 44)),  # 62 roof of house
    HitBox((0, 0), (64, 64)),  # 63 tree mid
    HitBox((0, 0), (64, 64)),  # 64 tree mid
    HitBox((4, 0), (16, 24)),  # 68 bottom of house
    HitBox((44, 0), (16, 24)),  # 70 bottom of house
    HitBox((0, 0), (64, 24)),  # 71 tree bottom
    HitBox((0, 0), (64, 24)),  # 72 tree bottom
    HitBox((52, 0), (12, 64)),  # 78 fence
    HitBox((0, 0), (12, 64)),  # 79 fence
    HitBox((0, 0), (64, 24)),  # 80 fence
    HitBox((12, 38), (52, 26)),  # 83 truck
    HitBox((0, 4), (64, 60)),  # 84 truck
    HitBox((0, 48), (56, 16)),  # 85 truck
    HitBox((0, 0), (64, 24)),  # 86 fence
    HitBox((0, 0), (64, 64)),  # 87 fence
    HitBox((0, 0), (64, 64)),  # 88 fence
    HitBox((8, 0), (56, 16)),  # 91 truck
    HitBox((8, 0), (48, 16)),  # 92 truck
    HitBox((0, 0), (56, 16)),  # 93 truck
    HitBox((0, 0), (64, 24)),  # 94 fence
    HitBox((0, 0), (64, 64)),  # 95 fence
    HitBox((0, 0), (64, 24)),  # 96 fence
]

# the centers of the tiles so they can be sorted by depth
tileCenters = {}
for i in range(97):
    tileCenters[i] = -9999999

playerHeightOffset = 1
tileCenters[2]  = 84 - playerHeightOffset  # large/tall fence top
tileCenters[9]  = 96 - playerHeightOffset  # wooden barrel
tileCenters[22] = 32 - playerHeightOffset  # wooden barrel

# creating the ground tiles (tile 8 is the origonal)
groundTiles = [
    tiles[8],
    pygame.transform.flip(tiles[8], False, True),
    pygame.transform.flip(tiles[8], True, False),
    pygame.transform.flip(tiles[8], True, True),
]

# creating a sprite for the bullet
bulletSprite = pygame.Surface([6, 6])
bulletSprite.set_colorkey((0, 0, 0))
pygame.draw.circle(bulletSprite, (125, 62, 0), (3, 3), 3)
pygame.draw.circle(bulletSprite, (255, 125, 0), (3, 3), 2)

# creating the various weapons
weaponSprites = Sprites.LoadSpritesheet(pygame.image.load("playerWeaponSpriteSheet.png"), (16, 16))
weaponSprites = Sprites.ScaleSprites(weaponSprites, (64, 64))

"""
playerWeapons = {
            "AR-15"        : Weapon("AR-15", 0.2, 100, 2, Bullet, 15, 2, Friendlies.friendly, AmoType.Rifle, maxLife=0.5, accuracy=0.1, selfKnockback=150, knockback=300, burst=1),
            "Glock-19"     : Weapon("Glock-19", -0.1, 75, 2.5, Bullet, 12, 1.5, Friendlies.friendly, AmoType.Pistol, maxLife=0.5, accuracy=0, selfKnockback=75, knockback=200, burst=1),
            "50-BMG"       : Weapon("50-BMG", -1.5, 125, 10, Bullet, 4, 3, Friendlies.friendly, AmoType.LargeRifle, maxLife=1, accuracy=0, selfKnockback=750, knockback=400, burst=1),
            "Remington-570": Weapon("Remington-570", -0.5, 75, 1, Bullet, 6, 3.5, Friendlies.friendly, AmoType.Shotgun, maxLife=0.2, accuracy=0.45, selfKnockback=125, knockback=300, burst=7),
            "MP-5"         : Weapon("MP-5", 0.055, 75, 0.75, Bullet, 65, 3, Friendlies.friendly, AmoType.Rifle, maxLife=0.45, accuracy=0.2, selfKnockback=25, knockback=125, burst=1)
}
"""
playerWeapons = {
            "SAR"           : Weapon("SAR"           , -0.25, 100, 1.5 , Bullet, 12, 2   , Friendlies.friendly, AmoType.Rifle  , maxLife=0.5 , accuracy=0.1 , selfKnockback=150, knockback=300, burst=1),
            "Pipe Pistol"   : Weapon("Pipe Pistol"   , -0.2 , 75 , 1   , Bullet, 6 , 1.75, Friendlies.friendly, AmoType.Pistol , maxLife=0.5 , accuracy=0   , selfKnockback=75 , knockback=200, burst=1),
            "Pipe Shotty"   : Weapon("Pipe Shotty"   , -0.75, 75 , 0.5 , Bullet, 2 , 3.5 , Friendlies.friendly, AmoType.Shotgun, maxLife=0.2 , accuracy=0.55, selfKnockback=125, knockback=300, burst=7),
            "Rusty Revolver": Weapon("Rusty Revolver", -0.15, 90 , 1.75, Bullet, 6 , 2.5 , Friendlies.friendly, AmoType.Pistol , maxLife=0.25, accuracy=0.05, selfKnockback=325, knockback=350, burst=1),
}

mobWeapons = {
    "Pipe Pistol": Weapon("Pipe Pistol", 2, 65, 3, Bullet, 99999999, 0, Friendlies.enemy, AmoType.Pistol, -999999, maxLife=0.5, accuracy=0.2, selfKnockback=175, knockback=-350, burst=1),
    "Pipe Shotty": Weapon("Pipe Shotty", 5, 55, 2, Bullet, 99999999, 0, Friendlies.enemy, AmoType.Shotgun, -999999, maxLife=0.5, accuracy=0.5, selfKnockback=60, knockback=-200, burst=6)
}

# armor sprites
armorItemSprites = Sprites.LoadSpritesheet(pygame.image.load("ArmorItems.png"), (16, 16))
armorItemSprites = Sprites.ScaleSprites(armorItemSprites, (48, 48))
playerArmors = {
    "Wooden Plate": Armor("Wooden Plate", armorItemSprites[0], 0.05),
    "Rusty Plate": Armor("Rusty Plate", armorItemSprites[1], 0.1),
    "Steel Plate": Armor("Steel Plate", armorItemSprites[2], 0.2)
}

# creating a sprite for a spark
sparkSprite = pygame.Surface((12, 12))
sparkSprite.set_colorkey((0, 0, 0))
pygame.draw.circle(sparkSprite, (255, 200, 0), (6, 6), 6)

# creating the player
playerSprites = Sprites.LoadSpritesheet(pygame.image.load("CharacterSpriteSheet.png"), (16, 16))
playerSprites = Sprites.ScaleSprites(playerSprites, (64, 64))
player = Player(playerSprites, light)
cameraPos = [600, 325]

# loading amo sprites
amoSprites = Sprites.LoadSpritesheet(pygame.image.load("amoSpriteSheet.png"), (6, 6))
amoSprites = Sprites.ScaleSprites(amoSprites, (18, 18))

# part drops
partDropSprites = Sprites.LoadSpritesheet(pygame.image.load("ShooterPartsSheet.png"), (8, 8))
partDropSprites = Sprites.ScaleSprites(partDropSprites, (24, 24))
partNames = ["Rusty Pipe", "Scrap Metal", "Rusty Nails", "Wire Spool", "Wood", "Gunpowder", "Metal Pipe", "Metal Sheet", "Nails", "Brass Casings", "Jerry Can", "Oil Can", "Spring", "blank", "blank", "blank", "blank", "Fire Powder"]
partDropSpritesDoubleScale = Sprites.ScaleSprites(partDropSprites, (48, 48))

for name in partNames:  # a hack to start the player with a ton of items to test crafting
    if name != "blank": player.AddPart(name, 25)

# crafting recipes and stuff
weaponItemSprites = Sprites.ScaleSprites(Sprites.LoadSpritesheet(pygame.image.load("WeaponItemSprites.png"), (16, 16)), (48, 48))
craftingRecipesTier1 = [
    CraftingRecipe([["Rusty Pipe", 2], ["Wire Spool", 4], ["Wood", 2], ["Rusty Nails", 6], ["Scrap Metal", 5]], DropTypes.Weapon, "Pipe Shotty", 1, weaponItemSprites[2]),
    CraftingRecipe([["Rusty Pipe", 1], ["Wire Spool", 6], ["Wood", 2], ["Rusty Nails", 10], ["Scrap Metal", 6], ["Spring", 1]], DropTypes.Weapon, "Rusty Revolver", 1, weaponItemSprites[3]),
    CraftingRecipe([["Rusty Pipe", 1], ["Wire Spool", 10], ["Wood", 4], ["Rusty Nails", 14], ["Scrap Metal", 9], ["Spring", 5]], DropTypes.Weapon, "SAR", 1, weaponItemSprites[0]),
    CraftingRecipe([["Wood", 12], ["Rusty Nails", 6]], DropTypes.Armor, "Wooden Plate", 12, armorItemSprites[0]),
    CraftingRecipe([["Scrap Metal", 8], ["Rusty Nails", 12], ["Wire Spool", 2]], DropTypes.Armor, "Rusty Plate", 12, armorItemSprites[1]),
    CraftingRecipe([["Brass Casings", 1], ["Rusty Nails", 2]], DropTypes.Amo, AmoType.Shotgun, 12, pygame.transform.scale(amoSprites[2], (48, 48))),
    CraftingRecipe([["Brass Casings", 1], ["Rusty Nails", 1]], DropTypes.Amo, AmoType.Pistol, 12, pygame.transform.scale(amoSprites[0], (48, 48))),
    CraftingRecipe([["Brass Casings", 1], ["Rusty Nails", 1]], DropTypes.Amo, AmoType.Rifle, 8, pygame.transform.scale(amoSprites[3], (48, 48))),
    CraftingRecipe([["Brass Casings", 1], ["Rusty Nails", 1]], DropTypes.Amo, AmoType.LargeRifle, 4, pygame.transform.scale(amoSprites[1], (48, 48))),
]
tier1CraftingTiles = [19, 20, 27, 28]  # the tile numbers for the tier 1 crafting table

# loading the sprites and animation for zombies
zombieSprites = Sprites.LoadSpritesheet(pygame.image.load("zombieSpritesheet.png"), (16, 16))
zombieSprites = Sprites.ScaleSprites(zombieSprites, (64, 64))
zombieDrops = [
    [DropTypes.Amo, AmoType.Pistol, (3, 14), 5],  # drop type, name, amount range, chance (0-10)
    [DropTypes.Amo, AmoType.LargeRifle, (1, 3), 2],
    [DropTypes.Amo, AmoType.Rifle, (4, 8), 7],
    [DropTypes.Amo, AmoType.Shotgun, (2, 5), 4],
    [DropTypes.Part, "Rusty Pipe", (1, 1), 2],
    [DropTypes.Part, "Scrap Metal", (1, 2), 1.5],
    [DropTypes.Part, "Rusty Nails", (1, 2), 1],
    [DropTypes.Part, "Brass Casings", (0, 1), 1],
    [DropTypes.Part, "Wood", (1, 2), 3],
    [DropTypes.Part, "Wire Spool", (0, 1), 1],
    [DropTypes.Part, "Spring", (0, 1), 0.75],
]
mobs = []

# drops for various storage containers (amo crates and barrels)
woodenBarrelDrops = [
    [DropTypes.Part, "Rusty Pipe", (1, 2), 5.5],  # drop type, name, amount range, chance (0-10)
    [DropTypes.Part, "Scrap Metal", (1, 3), 4],
    [DropTypes.Part, "Rusty Nails", (1, 4), 5],
    [DropTypes.Part, "Wood", (1, 9), 8],
    [DropTypes.Part, "Wire Spool", (1, 2), 3],
    [DropTypes.Part, "Spring", (1, 1), 2],
]

amoCrateDrops = [
    [DropTypes.Amo, AmoType.Pistol, (14, 32), 7.5],  # drop type, name, amount range, chance (0-10)
    [DropTypes.Amo, AmoType.LargeRifle, (2, 9), 5],
    [DropTypes.Amo, AmoType.Rifle, (13, 25), 7.5],
    [DropTypes.Amo, AmoType.Shotgun, (5, 14), 6.25],
]

# all the solid objects
#solidObjects = [
#    ShadowedObject([64*3, 64*9], [64, 64], sprite=tiles[1], renderShadows=True),
#    ShadowedObject([64*6, 64*12], [64, 64], sprite=tiles[1], renderShadows=True),
#    ShadowedObject(((21-2)*64, (13-4)*64), [64*2, 64*4], renderObject=False, collideable=False),
#]tileMap

# all the light sources around the map
#lights = [
#    #Light(125, (225, 225, 175), 1, False, (500, 250))
#    Light(200, (225, 225, 175), 1, False, (64*5 + 32, 64*5 + 32)),  # top left lanturn
#    Light(200, (225, 225, 175), 1, False, (64*17 + 32, 64*14 + 32))  # top left lanturn
#]

# loading the first level
tileMap=None
solidObjects=None
lights=None
LoadLevel("ShooterL1")  # loads all the data from the save files for the level

# creating the screen
screenSize = (1200, 750)
screen = pygame.display.set_mode(screenSize, flags=pygame.RESIZABLE)

# creating an event manager
events = Events.Manager()

# some time related things
dt = 1/120
fps = 0
desiredTime = 0  # 0 is unlimited, 1 / fps limits it to the fps desired
lastCheckedFps = time.time()

"""
lowest = 0
heighest = 0
lastReset = time.time()
"""

# =============================================================================
#                               Main Game Loop
#=============================================================================


# running the game
while True:
    # the start of the frame
    frameStart = time.time()
    
    # getting the size of the screen (incase it got scaled or something)
    screenSize = screen.get_size()

    # updating the events
    events.GetEvents()
    
    # updaing the fps counter
    if time.time() - lastCheckedFps > 0.1:
        lastCheckedFps = time.time()
        fps = round(1 / dt)

    """
    if time.time() - lastReset > 1:
        lowest = fps
        heighest = fps
        lastReset = time.time()
    lowest = min(lowest, fps)
    heighest = max(heighest, fps)
    """
    
    # updating the player
    player.Update(events, dt)

    # updating the mobs
    for enemy in mobs:
        enemy.Update(events, dt)
    
    # spawing enimies randomly
    if random.randint(0, round(25000*3 * dt)) == 0 and not len(mobs):
        for i in range(random.randint(5, 9)):
            mob = Enemy(zombieSprites, [random.randint(100, 1100), random.randint(100, 650)], 1, 35, random.randint(1, 5), zombieDrops, weapon=mobWeapons[["Pipe Pistol", "Pipe Shotty"][random.randint(0, 1)]].Copy())
            mobs.append(mob)
    
    # updating the camera position
    cameraPos = [Mix(cameraPos[0], player.position[0], dt * 5), Mix(cameraPos[1], player.position[1], dt * 5)]

    # drawing the base layer ground
    screen.fill((0, 0, 0))  # the base layer

    # rendering the gravel ground
    topLeft = [cameraPos[0] - screenSize[0]//2, cameraPos[1] - screenSize[1]//2]
    topLeftStart = [-(topLeft[0] % tileMap.tileSize), -(topLeft[1] % tileMap.tileSize)]
    dstAcross = [math.ceil(screenSize[0]/tileMap.tileSize), math.ceil(screenSize[1]/tileMap.tileSize)]
    bx, by = topLeft[0]//tileMap.tileSize, topLeft[1]//tileMap.tileSize
    for x in range(dstAcross[0]+1):
        for y in range(dstAcross[1]+1):
            screen.blit(groundTiles[round((x+y+bx+by)%4)], [round(topLeftStart[0]+x*64), round(topLeftStart[1]+y*64)])
    
    # creating the light map
    lightMap = pygame.Surface(screenSize)
    #lightMap.fill((10, 45, 20))  # good for night vision
    
    # rendering all the lights
    for light in lights:
        light.Render(lightMap)

    # the depth map to layer tiles and objects correctly (let's you walk behind objects and entities or infront)
    depthMap = []

    # drawing the rest of the ground
    depthMap += tileMap.RenderDepth(screen, cameraPos, screenSize, tileCenters)

    # rendering the solid objects
    for obj in solidObjects:
        #obj.Render(screen)
        depth = obj.pos[1]
        depthMap.append([obj, depth, screen])
    
    # rendering the player
    #player.Render(screen, lightMap)
    depth = player.position[1]
    depthMap.append([player, depth, screen, lightMap])

    # rendering the mobs
    aliveEnemies = []
    for enemy in mobs:
        #enemy.Render(screen, lightMap)
        depth = enemy.position[1]
        depthMap.append([enemy, depth, screen, lightMap])
        if enemy.health > 0:
            aliveEnemies.append(enemy)
        else:  # killing the enemy
            enemy.Kill()

            randomLife = random.uniform(4.75, 7.5)
            for i in range(random.randint(*enemy.sparkRange)):
                x, y = random.randint(-100, 100), random.randint(-100, 100)
                length = math.sqrt(x*x + y*y)
                if not length: length = 1
                spark = SparksParticle(enemy.position[::], [x/length * 100, y/length * 100], randomLife + random.uniform(-0.25, 0.25))
                player.projectiles.append(spark)
    mobs = aliveEnemies

    # sorting and rendering the objects
    sortedDepthMap = sorted(depthMap, key=lambda args: args[1])
    for obj, depth, *args in sortedDepthMap:
        obj.Render(*args)

    # rendering the light map
    screen.blit(lightMap, [0, 0], special_flags=pygame.BLEND_MULT)

    # rendering the dash cooldown
    pygame.draw.rect(screen, (255, 255, 0), [8, 8, 104, 24])
    pygame.draw.rect(screen, (225, 255, 225), [10, 10, 100, 20])
    pygame.draw.rect(screen, (75, 75, 75), [10, 10, 100*(1 - min((time.time() - player.lastDashed) / player.stats["dashCooldown"], 1)), 20])
    UI.DrawText(screen, 15, "pixel2.ttf", f"DASH", (60, 20), (225, 0, 0), centered=True)

    # displaying the name of the held weapon
    UI.DrawText(screen, 30, "pixel2.ttf", player.weaponInventory[player.weaponSlot].name, (10, 40), (255, 0, 0))
    UI.DrawText(screen, 30, "pixel2.ttf", f"{player.weaponInventory[player.weaponSlot].capacityLeft} - {player.amoInventory[player.weaponInventory[player.weaponSlot].amoType]}", (10, 70), (255, 0, 0))
    UI.DrawText(screen, 30, "pixel2.ttf", f"{player.health}hp", (10, 100), (255, 0, 0))

    # rendering the player UI
    player.RenderUI(screen)

    # rendering the fps counter
    UI.DrawText(screen, 15, "pixel2.ttf", f"FPS {fps}", (screenSize[0] - 90, 10), (255, 0, 0))
    #UI.DrawText(screen, 15, "pixel2.ttf", f"FPS {lowest} - {heighest}", (screenSize[0] - 120, 10), (255, 0, 0))

    # updating the display
    pygame.display.update()

    # forcing the framerate to certain amounts
    dif = max(desiredTime - (time.time() - frameStart), 0)
    time.sleep(dif)
    frameEnd = time.time()
    dt = min(frameEnd - frameStart, 1/15)

