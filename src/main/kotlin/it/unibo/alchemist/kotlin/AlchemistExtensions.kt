package it.unibo.alchemist.kotlin

import it.unibo.alchemist.model.interfaces.Position
import it.unibo.alchemist.model.interfaces.Time

operator fun Position.get(i: Int) = getCoordinate(i)
operator fun Position.plus(other: Position) = add(other)
operator fun Position.minus(other: Position) = subtract(other)
operator fun Time.plus(other: Time) = sum(other)
operator fun Time.minus(other: Time) = subtract(other)
