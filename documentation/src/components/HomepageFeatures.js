import React from 'react'
import clsx from 'clsx'
import styles from './HomepageFeatures.module.css'

const FeatureList = [
  {
    title: 'Easy to Use',
    Svg: require('@site/static/img/banner_a.svg').default,
    description: (
      <>
        Badger was specifically designed for operators. You could re-run an
        optimization routine with just one command/click.
      </>
    ),
  },
  {
    title: 'Fast to Extend',
    Svg: require('@site/static/img/banner_b.svg').default,
    description: (
      <>
        Badger can be extended through its plugin system. Shape
        your optimization problem into a plugin in 5 minutes.
      </>
    ),
  },
  {
    title: 'Multiple Mode',
    Svg: require('@site/static/img/banner_c.svg').default,
    description: (
      <>
        Badger can be used as a library, a command line tool, or a GUI
        application. Use Badger the way you want.
      </>
    ),
  },
]

const Feature = ({ Svg, title, description }) => {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <Svg className={styles.featureSvg} alt={title} />
      </div>
      <div className="text--center padding-horiz--md">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  )
}

const HomepageFeatures = () => {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => {
            return (
              <Feature key={idx} {...props} />
            )
          })}
        </div>
      </div>
    </section>
  )
}

export default HomepageFeatures
