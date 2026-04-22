import React from 'react'
import { Autoplay, Navigation, Pagination } from 'swiper/modules'
import { Swiper, SwiperSlide } from 'swiper/react'
import Run1Url from '@site/static/img/gui/run_1.png'
import Run2Url from '@site/static/img/gui/run_2.png'
import Run2ExtUrl from '@site/static/img/gui/run_2_ext.png'
import 'swiper/css'
import 'swiper/css/navigation'
import 'swiper/css/pagination'

const BadgerCarousel = () => {
  return (
    <Swiper
      modules={[Autoplay, Navigation, Pagination]}
      spaceBetween={50}
      slidesPerView={1}
      autoplay={{
        delay: 5000,
        disableOnInteraction: false,
      }}
      pagination={{
        clickable: true,
      }}
      navigation
      loop
      style={{
        '--swiper-pagination-color': '#EEEEEE',
        '--swiper-navigation-color': '#EEEEEE',
      }}
    >
      <SwiperSlide>
        <img alt="Badger running the default sphere2d environment" src={Run1Url} />
      </SwiperSlide>
      <SwiperSlide>
        <img alt="Badger running the tutorial sphere3d environment" src={Run2Url} />
      </SwiperSlide>
      <SwiperSlide>
        <img alt="Badger running the tutorial sphere3d environment" src={Run2ExtUrl} />
      </SwiperSlide>
    </Swiper>
  )
}

export default BadgerCarousel
